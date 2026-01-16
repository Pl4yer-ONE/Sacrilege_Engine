"""Demo file validator."""

from pathlib import Path
from dataclasses import dataclass
from typing import Optional
import hashlib

from demoparser2 import DemoParser

from src.config import get_settings
from src.models import DemoHeader


@dataclass
class ValidationResult:
    """Result of demo validation."""
    valid: bool
    error: Optional[str] = None
    header: Optional[DemoHeader] = None
    file_hash: Optional[str] = None


class DemoValidator:
    """Validates CS2 demo files before processing."""
    
    # CS2 demo magic bytes
    MAGIC_BYTES = b'PBDEMS2\x00'
    
    # Supported versions (add as CS2 updates)
    SUPPORTED_VERSIONS = [
        "cs2",  # Generic CS2 demos
    ]
    
    def __init__(self):
        self.settings = get_settings()
        self.max_size = self.settings.max_demo_size_mb * 1024 * 1024
    
    def validate(self, file_path: Path) -> ValidationResult:
        """
        Validate a demo file.
        
        Steps:
        1. Check file exists and is readable
        2. Verify file size within limits
        3. Check magic bytes (demo header signature)
        4. Parse header for version compatibility
        5. Compute file hash
        """
        # Check file exists
        if not file_path.exists():
            return ValidationResult(valid=False, error="File not found")
        
        if not file_path.is_file():
            return ValidationResult(valid=False, error="Path is not a file")
        
        # Check file size
        file_size = file_path.stat().st_size
        if file_size > self.max_size:
            return ValidationResult(
                valid=False,
                error=f"File too large: {file_size // (1024*1024)}MB > {self.settings.max_demo_size_mb}MB"
            )
        
        if file_size < 100:
            return ValidationResult(valid=False, error="File too small to be valid demo")
        
        # Check magic bytes
        try:
            with open(file_path, 'rb') as f:
                magic = f.read(8)
                if magic != self.MAGIC_BYTES:
                    return ValidationResult(
                        valid=False,
                        error="Invalid demo format - not a CS2 demo file"
                    )
        except IOError as e:
            return ValidationResult(valid=False, error=f"Cannot read file: {e}")
        
        # Parse header using demoparser2
        try:
            header = self._parse_header(file_path)
        except Exception as e:
            return ValidationResult(valid=False, error=f"Corrupt demo header: {e}")
        
        # Compute file hash
        file_hash = self._compute_hash(file_path)
        
        return ValidationResult(
            valid=True,
            header=header,
            file_hash=file_hash
        )
    
    def _parse_header(self, file_path: Path) -> DemoHeader:
        """Parse demo header using demoparser2."""
        parser = DemoParser(str(file_path))
        
        # Get header info
        header_info = parser.parse_header()
        
        return DemoHeader(
            map_name=header_info.get("map_name", "unknown"),
            tick_rate=header_info.get("tickrate", 64.0),
            duration_ticks=header_info.get("playback_ticks", 0),
            duration_seconds=header_info.get("playback_time", 0.0),
            game_version=header_info.get("network_protocol", ""),
            server_name=header_info.get("server_name", ""),
        )
    
    def _compute_hash(self, file_path: Path) -> str:
        """Compute SHA-256 hash of demo file."""
        sha256 = hashlib.sha256()
        
        with open(file_path, 'rb') as f:
            # Read in chunks for large files
            for chunk in iter(lambda: f.read(8192), b''):
                sha256.update(chunk)
        
        return sha256.hexdigest()
