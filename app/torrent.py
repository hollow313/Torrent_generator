import os
import hashlib
import time
from typing import List, Dict, Any, Callable, Optional, Tuple

def bencode(obj: Any) -> bytes:
    """Encode Python objects to BitTorrent bencoded bytes."""
    if isinstance(obj, int):
        return f"i{obj}e".encode("ascii")
    elif isinstance(obj, str):
        b = obj.encode("utf-8")
        return f"{len(b)}:".encode("ascii") + b
    elif isinstance(obj, bytes):
        return f"{len(obj)}:".encode("ascii") + obj
    elif isinstance(obj, list):
        encoded_items = b"".join(bencode(item) for item in obj)
        return b"l" + encoded_items + b"e"
    elif isinstance(obj, dict):
        # Keys in BitTorrent bencoding must be sorted by raw byte comparison
        items = []
        for k in obj.keys():
            k_bytes = k.encode("utf-8") if isinstance(k, str) else k
            items.append((k_bytes, k))
        items.sort(key=lambda x: x[0])
        
        encoded_dict = b"d"
        for k_bytes, k in items:
            encoded_dict += bencode(k) + bencode(obj[k])
        encoded_dict += b"e"
        return encoded_dict
    else:
        raise TypeError(f"Unsupported type for bencoding: {type(obj)}")

def calculate_c411_piece_size(total_bytes: int, file_count: int = 1) -> int:
    """
    Calculate piece size based on C411 guidelines:
    - < 1 Go: 1 Mo (1048576)
    - < 2 Go: 2 Mo (2097152)
    - < 3 Go: 4 Mo (4194304)
    - < 8 Go: 8 Mo (8388608)
    - > 8 Go: 16 Mo (16777216)
    - If many files with low size, can use higher piece size.
    Never exceed 16 Mo.
    """
    GIB = 1024 * 1024 * 1024
    MIB = 1024 * 1024
    
    if total_bytes < 1 * GIB:
        if file_count > 50:
            return 2 * MIB
        return 1 * MIB
    elif total_bytes < 2 * GIB:
        return 2 * MIB
    elif total_bytes < 3 * GIB:
        return 4 * MIB
    elif total_bytes < 8 * GIB:
        return 8 * MIB
    else:
        return 16 * MIB

class TorrentBuilder:
    def __init__(
        self,
        source_path: str,
        release_name: str,
        primary_announce: str,
        backup_announce: Optional[str] = None,
        piece_size: Optional[int] = None,
        is_private: bool = True,
        source_tag: str = "C411",
        comment: str = "Created with Torrent Generator for C411",
        created_by: str = "TorrentGenerator/1.0"
    ):
        self.source_path = os.path.abspath(source_path)
        self.release_name = release_name
        self.primary_announce = primary_announce.strip()
        self.backup_announce = backup_announce.strip() if backup_announce else None
        self.is_private = is_private
        self.source_tag = source_tag
        self.comment = comment
        self.created_by = created_by
        
        self.is_dir = os.path.isdir(self.source_path)
        self.files_info: List[Tuple[str, int, List[str]]] = []  # (abs_path, size, rel_path_parts)
        self.total_size = 0
        
        self._scan_files()
        
        if piece_size and piece_size > 0:
            self.piece_size = piece_size
        else:
            self.piece_size = calculate_c411_piece_size(self.total_size, len(self.files_info))

    def _scan_files(self):
        if not os.path.exists(self.source_path):
            raise FileNotFoundError(f"Path not found: {self.source_path}")
            
        if not self.is_dir:
            size = os.path.getsize(self.source_path)
            self.files_info.append((self.source_path, size, [os.path.basename(self.source_path)]))
            self.total_size = size
        else:
            for root, dirs, files in os.walk(self.source_path):
                # Sort for deterministic ordering
                dirs.sort()
                files.sort()
                for file in files:
                    full_path = os.path.join(root, file)
                    rel_path = os.path.relpath(full_path, self.source_path)
                    parts = rel_path.replace("\\", "/").split("/")
                    size = os.path.getsize(full_path)
                    self.files_info.append((full_path, size, parts))
                    self.total_size += size

    def build(self, output_file: str, progress_callback: Optional[Callable[[float, int, int], None]] = None) -> Tuple[str, str]:
        """
        Builds the .torrent file and writes it to output_file.
        Returns: (output_path, info_hash_hex)
        """
        pieces_hashes = bytearray()
        hasher = hashlib.sha1()
        bytes_in_current_piece = 0
        total_bytes_processed = 0
        
        # Read files sequentially and generate SHA-1 pieces
        CHUNK_SIZE = 1024 * 1024 # 1 MB read buffer
        
        for file_path, file_size, _ in self.files_info:
            with open(file_path, "rb") as f:
                while True:
                    data = f.read(CHUNK_SIZE)
                    if not data:
                        break
                    
                    data_offset = 0
                    while data_offset < len(data):
                        needed = self.piece_size - bytes_in_current_piece
                        chunk = data[data_offset : data_offset + needed]
                        hasher.update(chunk)
                        chunk_len = len(chunk)
                        bytes_in_current_piece += chunk_len
                        data_offset += chunk_len
                        total_bytes_processed += chunk_len
                        
                        if bytes_in_current_piece == self.piece_size:
                            pieces_hashes.extend(hasher.digest())
                            hasher = hashlib.sha1()
                            bytes_in_current_piece = 0
                            
                            if progress_callback and self.total_size > 0:
                                pct = (total_bytes_processed / self.total_size) * 100
                                progress_callback(pct, total_bytes_processed, self.total_size)

        # Final piece if remaining bytes exist
        if bytes_in_current_piece > 0:
            pieces_hashes.extend(hasher.digest())
            if progress_callback and self.total_size > 0:
                progress_callback(100.0, total_bytes_processed, self.total_size)

        # Construct info dictionary
        info: Dict[str, Any] = {
            "piece length": self.piece_size,
            "pieces": bytes(pieces_hashes),
        }
        
        if self.is_private:
            info["private"] = 1
            
        if self.source_tag:
            info["source"] = self.source_tag
            
        if not self.is_dir:
            info["name"] = self.release_name or os.path.basename(self.source_path)
            info["length"] = self.total_size
        else:
            info["name"] = self.release_name or os.path.basename(self.source_path)
            torrent_files = []
            for _, size, parts in self.files_info:
                torrent_files.append({
                    "length": size,
                    "path": parts
                })
            info["files"] = torrent_files

        # Calculate infohash
        bencoded_info = bencode(info)
        info_hash = hashlib.sha1(bencoded_info).hexdigest()

        # Construct main torrent metadata
        torrent_meta: Dict[str, Any] = {
            "announce": self.primary_announce,
            "comment": self.comment,
            "created by": self.created_by,
            "creation date": int(time.time()),
            "info": info
        }

        # Announce-list (Multitracker BEP 0012)
        announce_list = [[self.primary_announce]]
        if self.backup_announce and self.backup_announce != self.primary_announce:
            announce_list.append([self.backup_announce])
        torrent_meta["announce-list"] = announce_list

        os.makedirs(os.path.dirname(os.path.abspath(output_file)), exist_ok=True)
        with open(output_file, "wb") as f:
            f.write(bencode(torrent_meta))
            
        return output_file, info_hash
