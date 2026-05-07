#!/usr/bin/env python3
"""
Database Backup and Maintenance Script for POS System
Creates automated backups of the SQLite database
"""

import os
import shutil
import sqlite3
import json
from datetime import datetime, timedelta
from pathlib import Path


class POSDatabaseManager:
    """Manage POS system database backups and maintenance"""

    def __init__(self, project_root):
        self.project_root = Path(project_root)
        self.db_path = self.project_root / "Server" / "backend" / "db.sqlite3"
        self.backup_dir = self.project_root / "Database" / "backups"
        self.dumps_dir = self.project_root / "Database" / "dumps"

    def setup_backup_dirs(self):
        """Create backup directories if they don't exist"""
        self.backup_dir.mkdir(parents=True, exist_ok=True)
        self.dumps_dir.mkdir(parents=True, exist_ok=True)
        print(f"✅ Backup directories ready")
        print(f"   - Backups: {self.backup_dir}")
        print(f"   - Dumps: {self.dumps_dir}")

    def create_backup(self, backup_type="daily"):
        """Create a backup of the database"""
        if not self.db_path.exists():
            print(f"❌ Database not found: {self.db_path}")
            return False

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_filename = f"db_{backup_type}_{timestamp}.sqlite3"
        backup_path = self.backup_dir / backup_filename

        try:
            shutil.copy2(self.db_path, backup_path)
            file_size = backup_path.stat().st_size / 1024  # KB
            print(f"✅ Backup created: {backup_filename} ({file_size:.2f} KB)")
            return True
        except Exception as e:
            print(f"❌ Backup failed: {e}")
            return False

    def get_database_stats(self):
        """Get statistics about the database"""
        if not self.db_path.exists():
            print(f"❌ Database not found")
            return None

        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            # Get table information
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'")
            tables = cursor.fetchall()

            stats = {
                "timestamp": datetime.now().isoformat(),
                "database_file": str(self.db_path),
                "file_size_kb": self.db_path.stat().st_size / 1024,
                "tables": {}
            }

            for (table_name,) in tables:
                try:
                    cursor.execute(f"SELECT COUNT(*) FROM {table_name}")
                    row_count = cursor.fetchone()[0]
                    stats["tables"][table_name] = {
                        "rows": row_count
                    }
                except Exception as e:
                    stats["tables"][table_name] = {"error": str(e)}

            conn.close()
            return stats

        except Exception as e:
            print(f"❌ Failed to get stats: {e}")
            return None

    def print_stats(self):
        """Print database statistics"""
        stats = self.get_database_stats()
        if not stats:
            return

        print("\n" + "=" * 70)
        print("📊 DATABASE STATISTICS")
        print("=" * 70)
        print(f"Database: {self.db_path.name}")
        print(f"Size: {stats['file_size_kb']:.2f} KB")
        print(f"Last Updated: {stats['timestamp']}")
        print("\nTable Row Counts:")
        print("-" * 70)

        total_rows = 0
        for table_name in sorted(stats['tables'].keys()):
            info = stats['tables'][table_name]
            if 'rows' in info:
                row_count = info['rows']
                total_rows += row_count
                print(f"  {table_name:<30} {row_count:>10,} rows")
            else:
                print(f"  {table_name:<30} [Error reading]")

        print("-" * 70)
        print(f"  {'TOTAL':<30} {total_rows:>10,} rows")
        print("=" * 70 + "\n")

    def export_stats_json(self):
        """Export statistics to JSON file"""
        stats = self.get_database_stats()
        if not stats:
            return False

        stats_file = self.dumps_dir / f"db_stats_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        try:
            with open(stats_file, 'w') as f:
                json.dump(stats, f, indent=2)
            print(f"✅ Stats exported: {stats_file.name}")
            return True
        except Exception as e:
            print(f"❌ Failed to export stats: {e}")
            return False

    def cleanup_old_backups(self, days_to_keep=30):
        """Remove backups older than specified days"""
        if not self.backup_dir.exists():
            print("❌ Backup directory not found")
            return

        cutoff_date = datetime.now() - timedelta(days=days_to_keep)
        removed_count = 0

        for backup_file in self.backup_dir.glob("db_*.sqlite3"):
            file_mtime = datetime.fromtimestamp(backup_file.stat().st_mtime)
            if file_mtime < cutoff_date:
                try:
                    backup_file.unlink()
                    removed_count += 1
                except Exception as e:
                    print(f"❌ Failed to remove {backup_file.name}: {e}")

        print(f"✅ Cleanup complete: removed {removed_count} old backup(s)")

    def restore_from_backup(self, backup_filename):
        """Restore database from a backup"""
        backup_path = self.backup_dir / backup_filename

        if not backup_path.exists():
            print(f"❌ Backup file not found: {backup_filename}")
            return False

        try:
            # Create a recovery backup first
            shutil.copy2(self.db_path, self.db_path.with_suffix('.recovery'))
            shutil.copy2(backup_path, self.db_path)
            print(f"✅ Database restored from: {backup_filename}")
            print(f"   Original backed up to: db.sqlite3.recovery")
            return True
        except Exception as e:
            print(f"❌ Restore failed: {e}")
            return False

    def list_backups(self):
        """List all available backups"""
        if not self.backup_dir.exists():
            print("❌ Backup directory not found")
            return

        backups = sorted(self.backup_dir.glob("db_*.sqlite3"), reverse=True)

        if not backups:
            print("No backups found")
            return

        print("\n" + "=" * 70)
        print("📦 AVAILABLE BACKUPS")
        print("=" * 70)

        for i, backup in enumerate(backups[:10], 1):  # Show last 10
            file_size = backup.stat().st_size / 1024  # KB
            file_mtime = datetime.fromtimestamp(backup.stat().st_mtime)
            print(f"{i}. {backup.name:<50} {file_size:>10.2f} KB  {file_mtime.strftime('%Y-%m-%d %H:%M:%S')}")

        if len(backups) > 10:
            print(f"   ... and {len(backups) - 10} more backup(s)")
        print("=" * 70 + "\n")

    def health_check(self):
        """Perform database health check"""
        if not self.db_path.exists():
            print(f"❌ Database not found: {self.db_path}")
            return False

        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            # Run integrity check
            cursor.execute("PRAGMA integrity_check")
            result = cursor.fetchone()[0]

            if result == "ok":
                print("✅ Database integrity: OK")
                return True
            else:
                print(f"⚠️  Database integrity issues: {result}")
                return False

        except Exception as e:
            print(f"❌ Health check failed: {e}")
            return False
        finally:
            conn.close()


def main():
    """Main function"""
    import sys

    project_root = Path("c:\\Users\\DELL\\Desktop\\Roe's POS")

    manager = POSDatabaseManager(project_root)
    manager.setup_backup_dirs()

    print("\n" + "=" * 70)
    print("🗄️  POS DATABASE MANAGEMENT TOOL")
    print("=" * 70)

    # Run checks
    print("\n1️⃣  Running health check...")
    manager.health_check()

    print("\n2️⃣  Getting database statistics...")
    manager.print_stats()

    print("\n3️⃣  Creating backup...")
    manager.create_backup("daily")

    print("\n4️⃣  Listing recent backups...")
    manager.list_backups()

    print("\n5️⃣  Exporting statistics...")
    manager.export_stats_json()

    print("\n6️⃣  Cleaning up old backups (>30 days)...")
    manager.cleanup_old_backups(days_to_keep=30)

    print("\n" + "=" * 70)
    print("✅ Database maintenance complete!")
    print("=" * 70)


if __name__ == "__main__":
    main()