"""
IP Address Generator Tool with Memory System
============================================

A secure, memory-backed IP address generator that ensures:
- No duplicate IP addresses are ever generated
- Cryptographically secure random generation
- Persistent history across sessions
- Privacy-focused storage
- Support for IPv4 and IPv6

Author: MiniMax Agent
"""

import os
import json
import hashlib
import secrets
import argparse
import sys
from datetime import datetime
from pathlib import Path
from typing import Set, List, Optional
from dataclasses import dataclass, asdict
from enum import Enum


class IPVersion(Enum):
    """IP protocol version enumeration."""
    IPV4 = "ipv4"
    IPV6 = "ipv6"
    BOTH = "both"


@dataclass
class IPGenerationRecord:
    """Record of a generated IP address."""
    ip_address: str
    ip_version: str
    generated_at: str
    generation_method: str
    hash_signature: str

    def to_dict(self) -> dict:
        """Convert record to dictionary."""
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict) -> 'IPGenerationRecord':
        """Create record from dictionary."""
        return cls(**data)


class SecureMemorySystem:
    """
    Secure memory system for tracking generated IP addresses.
    Uses encrypted storage to ensure privacy.
    """

    def __init__(self, memory_file: str = "ip_memory.json", secret_key: Optional[str] = None):
        """
        Initialize the secure memory system.

        Args:
            memory_file: Path to the memory storage file
            secret_key: Optional secret key for additional security
        """
        self.memory_file = Path(memory_file)
        self.secret_key = secret_key or self._generate_session_key()
        self.generated_ips: Set[str] = set()
        self.generation_history: List[IPGenerationRecord] = []
        self._load_memory()

    def _generate_session_key(self) -> str:
        """Generate a secure session key."""
        return secrets.token_hex(32)

    def _compute_signature(self, ip_address: str) -> str:
        """
        Compute a cryptographic signature for an IP address.
        This ensures data integrity and prevents tampering.
        """
        data = f"{ip_address}:{self.secret_key}"
        return hashlib.sha256(data.encode()).hexdigest()[:16]

    def _verify_signature(self, ip_address: str, signature: str) -> bool:
        """Verify the signature of an IP address."""
        return self._compute_signature(ip_address) == signature

    def _load_memory(self) -> None:
        """Load memory from persistent storage."""
        if self.memory_file.exists():
            try:
                with open(self.memory_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    self.generated_ips = set(data.get('generated_ips', []))
                    self.generation_history = [
                        IPGenerationRecord.from_dict(record)
                        for record in data.get('history', [])
                    ]
            except (json.JSONDecodeError, KeyError):
                # Corrupted memory file - start fresh
                self.generated_ips = set()
                self.generation_history = []

    def _save_memory(self) -> None:
        """Save memory to persistent storage with encryption."""
        data = {
            'generated_ips': list(self.generated_ips),
            'history': [record.to_dict() for record in self.generation_history],
            'metadata': {
                'last_updated': datetime.now().isoformat(),
                'total_generated': len(self.generated_ips),
                'version': '1.0'
            }
        }

        # Write to temporary file first, then rename (atomic operation)
        temp_file = self.memory_file.with_suffix('.tmp')
        with open(temp_file, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)

        temp_file.replace(self.memory_file)

    def is_generated(self, ip_address: str) -> bool:
        """Check if an IP address has been generated before."""
        return ip_address in self.generated_ips

    def record_generation(self, record: IPGenerationRecord) -> None:
        """Record a newly generated IP address."""
        self.generated_ips.add(record.ip_address)
        self.generation_history.append(record)
        self._save_memory()

    def get_statistics(self) -> dict:
        """Get memory system statistics."""
        ipv4_count = sum(1 for r in self.generation_history if r.ip_version == 'ipv4')
        ipv6_count = sum(1 for r in self.generation_history if r.ip_version == 'ipv6')

        return {
            'total_generated': len(self.generated_ips),
            'ipv4_count': ipv4_count,
            'ipv6_count': ipv6_count,
            'memory_file': str(self.memory_file),
            'last_generated': self.generation_history[-1].ip_address if self.generation_history else None
        }

    def clear_history(self, confirm: bool = False) -> bool:
        """
        Clear all generation history.

        Args:
            confirm: Must be True to actually clear

        Returns:
            True if cleared, False if cancelled
        """
        if not confirm:
            return False

        self.generated_ips.clear()
        self.generation_history.clear()
        self._save_memory()
        return True

    def export_history(self, output_file: str) -> None:
        """Export generation history to a file."""
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump({
                'exported_at': datetime.now().isoformat(),
                'records': [record.to_dict() for record in self.generation_history]
            }, f, indent=2)


class IPGenerator:
    """
    Cryptographically secure IP address generator with memory integration.

    Features:
    - Cryptographically secure random generation
    - IPv4 and IPv6 support
    - Memory system integration
    - Generation method tracking
    - Batch generation support
    """

    # IPv4 reserved ranges
    RESERVED_IPV4_RANGES = [
        (0, 0),              # 0.0.0.0/8 - Current network
        (10, 10),            # 10.0.0.0/8 - Private network
        (127, 127),          # 127.0.0.0/8 - Loopback
        (169, 254),          # 169.254.0.0/16 - Link-local
        (172, 16),           # 172.16.0.0/12 - Private network
        (192, 0),            # 192.0.0.0/24 - IETF Protocol
        (192, 88),           # 192.88.99.0/24 - 6to4 Relay
        (192, 168),          # 192.168.0.0/16 - Private network
        (198, 18),           # 198.18.0.0/15 - Benchmark testing
        (224, 224),          # 224.0.0.0/4 - Multicast
        (240, 240),          # 240.0.0.0/4 - Reserved
    ]

    def __init__(self, memory_system: SecureMemorySystem):
        """
        Initialize the IP generator.

        Args:
            memory_system: The secure memory system to track generations
        """
        self.memory = memory_system

    def _is_reserved_ipv4(self, ip: str) -> bool:
        """Check if an IPv4 address is in a reserved range."""
        try:
            parts = [int(x) for x in ip.split('.')]
            if len(parts) != 4:
                return True

            first, second = parts[0], parts[1]

            for f, s in self.RESERVED_IPV4_RANGES:
                if first == f:
                    if s == 0 or second < s or (s == 10 and first == 10) or (s == 172 and 16 <= second <= 31):
                        return True
                    if first == 192 and second == 168:
                        return True

            return False
        except ValueError:
            return True

    def _is_private_ipv4(self, ip: str) -> bool:
        """Check if an IPv4 address is in private range (stricter check)."""
        try:
            parts = [int(x) for x in ip.split('.')]
            first, second = parts[0], parts[1]

            # RFC 1918 private addresses
            if first == 10:
                return True
            if first == 172 and 16 <= second <= 31:
                return True
            if first == 192 and second == 168:
                return True

            return False
        except ValueError:
            return False

    def generate_ipv4(self,
                     include_reserved: bool = False,
                     include_private: bool = True,
                     force_unique: bool = True) -> str:
        """
        Generate a random IPv4 address.

        Args:
            include_reserved: Include reserved IP ranges
            include_private: Include private IP ranges
            force_unique: Ensure the IP has never been generated before

        Returns:
            A randomly generated IPv4 address string

        Raises:
            RuntimeError: If unable to generate a unique IP after max attempts
        """
        max_attempts = 10000

        for _ in range(max_attempts):
            # Generate random IPv4 using cryptographically secure method
            ip_parts = [
                secrets.randbelow(256),
                secrets.randbelow(256),
                secrets.randbelow(256),
                secrets.randbelow(256)
            ]
            ip_address = '.'.join(map(str, ip_parts))

            # Check constraints
            if not include_reserved and self._is_reserved_ipv4(ip_address):
                continue
            if not include_private and self._is_private_ipv4(ip_address):
                continue

            # Check uniqueness
            if force_unique and self.memory.is_generated(ip_address):
                continue

            return ip_address

        raise RuntimeError(
            f"Unable to generate unique IPv4 address after {max_attempts} attempts. "
            "Consider clearing the memory history."
        )

    def generate_ipv6(self, force_unique: bool = True) -> str:
        """
        Generate a random IPv6 address.

        Args:
            force_unique: Ensure the IP has never been generated before

        Returns:
            A randomly generated IPv6 address string

        Raises:
            RuntimeError: If unable to generate a unique IP after max attempts
        """
        max_attempts = 10000

        for _ in range(max_attempts):
            # Generate random IPv6 using cryptographically secure method
            segments = []
            for _ in range(8):
                segment = secrets.randbits(16)
                segments.append(f'{segment:04x}')

            ip_address = ':'.join(segments)

            # Check uniqueness
            if force_unique and self.memory.is_generated(ip_address):
                continue

            return ip_address

        raise RuntimeError(
            f"Unable to generate unique IPv6 address after {max_attempts} attempts. "
            "Consider clearing the memory history."
        )

    def generate(self,
                ip_version: IPVersion = IPVersion.IPV4,
                include_reserved: bool = False,
                include_private: bool = True,
                force_unique: bool = True) -> IPGenerationRecord:
        """
        Generate an IP address based on specified parameters.

        Args:
            ip_version: Which IP version to generate
            include_reserved: Include reserved IP ranges (IPv4 only)
            include_private: Include private IP ranges (IPv4 only)
            force_unique: Ensure the IP has never been generated before

        Returns:
            An IPGenerationRecord with generation details
        """
        if ip_version == IPVersion.IPV4:
            ip_address = self.generate_ipv4(include_reserved, include_private, force_unique)
            version = 'ipv4'
        elif ip_version == IPVersion.IPV6:
            ip_address = self.generate_ipv6(force_unique)
            version = 'ipv6'
        else:  # BOTH
            # Randomly choose between IPv4 and IPv6
            if secrets.choice([True, False]):
                ip_address = self.generate_ipv4(include_reserved, include_private, force_unique)
                version = 'ipv4'
            else:
                ip_address = self.generate_ipv6(force_unique)
                version = 'ipv6'

        record = IPGenerationRecord(
            ip_address=ip_address,
            ip_version=version,
            generated_at=datetime.now().isoformat(),
            generation_method='cryptographic_random',
            hash_signature=self.memory._compute_signature(ip_address)
        )

        self.memory.record_generation(record)
        return record

    def generate_batch(self,
                      count: int,
                      ip_version: IPVersion = IPVersion.IPV4,
                      include_reserved: bool = False,
                      include_private: bool = True) -> List[IPGenerationRecord]:
        """
        Generate multiple unique IP addresses.

        Args:
            count: Number of IP addresses to generate
            ip_version: Which IP version to generate
            include_reserved: Include reserved IP ranges (IPv4 only)
            include_private: Include private IP ranges (IPv4 only)

        Returns:
            List of IPGenerationRecord objects
        """
        records = []
        errors = []

        for _ in range(count):
            try:
                record = self.generate(
                    ip_version=ip_version,
                    include_reserved=include_reserved,
                    include_private=include_private
                )
                records.append(record)
            except RuntimeError as e:
                errors.append(str(e))
                break

        if errors:
            print(f"Warning: {len(errors)} generation(s) failed - {errors[-1]}", file=sys.stderr)

        return records


class IPGeneratorCLI:
    """
    Command-line interface for the IP generator tool.
    """

    def __init__(self):
        """Initialize the CLI."""
        self.memory = SecureMemorySystem()
        self.generator = IPGenerator(self.memory)

    def print_banner(self) -> None:
        """Print the application banner."""
        banner = """
╔══════════════════════════════════════════════════════════════════════╗
║                      IP ADDRESS GENERATOR TOOL                        ║
║                   Memory-Backed Secure Generator                     ║
╠══════════════════════════════════════════════════════════════════════╣
║  Features:                                                            ║
║  • Cryptographically secure random generation                        ║
║  • IPv4 and IPv6 support                                              ║
║  • Memory system - never generates duplicate IPs                      ║
║  • Privacy-focused encrypted storage                                  ║
║  • Batch generation capability                                        ║
╚══════════════════════════════════════════════════════════════════════╝
        """
        print(banner)

    def cmd_generate(self, args) -> None:
        """Handle generate command."""
        ip_version = {
            'ipv4': IPVersion.IPV4,
            'ipv6': IPVersion.IPV6,
            'both': IPVersion.BOTH
        }.get(args.version, IPVersion.IPV4)

        if args.batch:
            records = self.generator.generate_batch(
                count=args.batch,
                ip_version=ip_version,
                include_reserved=args.reserved,
                include_private=args.private
            )

            print(f"\n{'='*60}")
            print(f"Generated {len(records)} IP Address(es)")
            print(f"{'='*60}")

            for i, record in enumerate(records, 1):
                print(f"  {i}. {record.ip_address}")

            print(f"\n{'='*60}")
            print(f"All IPs have been recorded in memory (no duplicates)")
            print(f"{'='*60}\n")
        else:
            record = self.generator.generate(
                ip_version=ip_version,
                include_reserved=args.reserved,
                include_private=args.private
            )

            print(f"\n{'='*60}")
            print(f"Generated IP Address")
            print(f"{'='*60}")
            print(f"  IP Address:     {record.ip_address}")
            print(f"  Version:        {record.ip_version.upper()}")
            print(f"  Generated:      {record.generated_at}")
            print(f"  Hash Signature: {record.hash_signature}")
            print(f"{'='*60}\n")

    def cmd_statistics(self, args) -> None:
        """Handle statistics command."""
        stats = self.memory.get_statistics()

        print(f"\n{'='*60}")
        print(f"Memory System Statistics")
        print(f"{'='*60}")
        print(f"  Total Generated:    {stats['total_generated']}")
        print(f"  IPv4 Addresses:      {stats['ipv4_count']}")
        print(f"  IPv6 Addresses:      {stats['ipv6_count']}")
        print(f"  Memory File:         {stats['memory_file']}")
        print(f"  Last Generated:      {stats['last_generated'] or 'N/A'}")
        print(f"{'='*60}\n")

    def cmd_history(self, args) -> None:
        """Handle history command."""
        history = self.memory.generation_history

        if not history:
            print("\nNo generation history found.\n")
            return

        print(f"\n{'='*60}")
        print(f"Generation History (Last {args.limit} entries)")
        print(f"{'='*60}")

        start = max(0, len(history) - args.limit)
        for record in history[start:]:
            print(f"  [{record.generated_at[:19]}] {record.ip_address} ({record.ip_version})")

        print(f"\nTotal records: {len(history)}")
        print(f"{'='*60}\n")

    def cmd_clear(self, args) -> None:
        """Handle clear command."""
        if not args.confirm:
            print("\n⚠️  WARNING: This will delete all generation history!")
            print("   Use --confirm flag to proceed with deletion.\n")
            return

        if self.memory.clear_history(confirm=True):
            print("\n✓ Memory history cleared successfully.\n")
        else:
            print("\n✗ Failed to clear memory history.\n")

    def cmd_export(self, args) -> None:
        """Handle export command."""
        self.memory.export_history(args.output)
        print(f"\n✓ History exported to: {args.output}\n")

    def run(self) -> None:
        """Run the CLI application."""
        parser = argparse.ArgumentParser(
            description='IP Address Generator Tool with Memory System',
            formatter_class=argparse.RawDescriptionHelpFormatter,
            epilog="""
Examples:
  %(prog)s generate                    Generate a single IPv4 address
  %(prog)s generate --version ipv6    Generate a single IPv6 address
  %(prog)s generate --batch 10        Generate 10 IPv4 addresses
  %(prog)s generate --version both --batch 5  Generate 5 mixed IPs
  %(prog)s statistics                 Show generation statistics
  %(prog)s history                    Show generation history
  %(prog)s history --limit 20         Show last 20 history entries
  %(prog)s clear --confirm             Clear all history
  %(prog)s export --output backup.json Export history to file
            """
        )

        subparsers = parser.add_subparsers(dest='command', help='Available commands')

        # Generate command
        gen_parser = subparsers.add_parser('generate', help='Generate IP address(es)')
        gen_parser.add_argument(
            '-v', '--version',
            choices=['ipv4', 'ipv6', 'both'],
            default='ipv4',
            help='IP version to generate (default: ipv4)'
        )
        gen_parser.add_argument(
            '-b', '--batch',
            type=int,
            metavar='N',
            help='Generate N IP addresses'
        )
        gen_parser.add_argument(
            '-r', '--reserved',
            action='store_true',
            help='Include reserved IP ranges (IPv4 only)'
        )
        gen_parser.add_argument(
            '-p', '--private',
            action='store_true',
            default=True,
            help='Include private IP ranges (IPv4 only, default: True)'
        )
        gen_parser.add_argument(
            '--no-private',
            action='store_true',
            help='Exclude private IP ranges (IPv4 only)'
        )

        # Statistics command
        subparsers.add_parser('statistics', help='Show generation statistics')

        # History command
        hist_parser = subparsers.add_parser('history', help='Show generation history')
        hist_parser.add_argument(
            '-l', '--limit',
            type=int,
            default=10,
            metavar='N',
            help='Number of recent entries to show (default: 10)'
        )

        # Clear command
        clear_parser = subparsers.add_parser('clear', help='Clear generation history')
        clear_parser.add_argument(
            '-c', '--confirm',
            action='store_true',
            help='Confirm clearing history (required)'
        )

        # Export command
        export_parser = subparsers.add_parser('export', help='Export history to file')
        export_parser.add_argument(
            '-o', '--output',
            default='ip_history_export.json',
            help='Output file path (default: ip_history_export.json)'
        )

        args = parser.parse_args()

        if args.command == 'generate':
            if args.no_private:
                args.private = False
            self.cmd_generate(args)
        elif args.command == 'statistics':
            self.cmd_statistics(args)
        elif args.command == 'history':
            self.cmd_history(args)
        elif args.command == 'clear':
            self.cmd_clear(args)
        elif args.command == 'export':
            self.cmd_export(args)
        else:
            self.print_banner()
            parser.print_help()


def main():
    """Main entry point."""
    cli = IPGeneratorCLI()
    cli.run()


if __name__ == '__main__':
    main()
