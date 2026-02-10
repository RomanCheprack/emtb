#!/usr/bin/env python3
"""
Full pipeline orchestrator for eMTB data processing workflow.

This script runs the complete data pipeline:
1. Run all scrapers
2. Check duplicates in raw JSON files
3. Standardize data
4. Deduplicate standardized data
5. Drop bike data from database
6. Migrate new data to database
7. Send email notification

All steps run in a transaction for safe rollback on failure.
"""

import sys
import os
import subprocess
import time
import traceback
from datetime import datetime
from pathlib import Path
from threading import Thread
from queue import Queue, Empty

# Add project root to path
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
sys.path.insert(0, project_root)

from dotenv import load_dotenv
from app import create_app
from app.extensions import db
from app.models import Bike, Brand, Source, BikeListing
# Import email notifier
sys.path.insert(0, os.path.join(project_root, 'scripts', 'utils'))
from email_notifier import send_pipeline_notification
from fix_chromedriver_cache import clear_chromedriver_cache


class PipelineStats:
    """Track pipeline execution statistics"""
    def __init__(self):
        self.stats = {}
        self.start_time = time.time()
        self.step_start_times = {}
    
    def add_step(self, step_name, status, **kwargs):
        """Add step statistics"""
        self.stats[step_name] = {
            'status': status,
            **kwargs
        }
    
    def start_step(self, step_name):
        """Mark the start of a step"""
        self.step_start_times[step_name] = time.time()
    
    def get_step_duration(self, step_name):
        """Get duration of a specific step in seconds"""
        if step_name in self.step_start_times:
            return time.time() - self.step_start_times[step_name]
        return 0
    
    def get_duration(self):
        """Get total execution duration in seconds"""
        return time.time() - self.start_time
    
    def to_dict(self):
        """Convert to dictionary for email notification"""
        return self.stats


def stream_output(pipe, output_queue, output_type='stdout', prefix=""):
    """Stream output from a pipe in real-time"""
    try:
        buffer = b''
        while True:
            chunk = pipe.read(1024)
            if not chunk:
                if buffer:
                    try:
                        line = buffer.decode('utf-8', errors='replace').rstrip()
                        if line:
                            output_queue.put((output_type, f"{prefix}{line}"))
                    except Exception:
                        pass
                break
            
            buffer += chunk
            
            while b'\n' in buffer:
                line_bytes, buffer = buffer.split(b'\n', 1)
                try:
                    line = line_bytes.decode('utf-8', errors='replace').rstrip()
                    if line:
                        output_queue.put((output_type, f"{prefix}{line}"))
                except Exception:
                    continue
        pipe.close()
    except Exception as e:
        output_queue.put(('error', f"Error streaming output: {e}"))


def run_command(command, description, cwd=None, stream_output_enabled=True):
    """
    Run a shell command with real-time output streaming.
    
    Args:
        command: Command to run (list of strings)
        description: Description of what's being run
        cwd: Working directory (defaults to project root)
        stream_output_enabled: Whether to stream output in real-time
    
    Returns:
        (success: bool, stdout: str, stderr: str)
    """
    # Timeout set to 7 hours (25200 seconds)
    timeout = 25200
    if cwd is None:
        cwd = project_root
    
    step_start_time = time.time()
    print(f"\n{'='*80}")
    print(f"▶️  {description}")
    print(f"   Started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"{'='*80}")
    sys.stdout.flush()
    
    stdout_lines = []
    stderr_lines = []
    
    try:
        # Set UTF-8 encoding for subprocess output (Windows compatibility)
        env = os.environ.copy()
        env['PYTHONIOENCODING'] = 'utf-8'
        env['PYTHONUTF8'] = '1'
        
        if stream_output_enabled:
            # Use Popen for real-time streaming
            # Note: Popen doesn't support timeout parameter - we handle it manually in the loop
            process = subprocess.Popen(
                command,
                cwd=cwd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                bufsize=0,  # Unbuffered for real-time output
                env=env
            )
            
            # Create queues for output
            output_queue = Queue()
            
            # Start threads to stream output
            # Note: stderr is often used for informational output, not just errors
            stdout_thread = Thread(target=stream_output, args=(process.stdout, output_queue, 'stdout', ""))
            stderr_thread = Thread(target=stream_output, args=(process.stderr, output_queue, 'stderr', ""))
            
            stdout_thread.daemon = True
            stderr_thread.daemon = True
            
            stdout_thread.start()
            stderr_thread.start()
            
            # Process output in real-time
            last_status_time = time.time()
            status_interval = 60  # Print status every minute for long-running commands
            
            while process.poll() is None:
                elapsed = time.time() - step_start_time
                
                # Check for timeout (7 hours)
                if elapsed >= timeout:
                    process.terminate()
                    time.sleep(2)
                    if process.poll() is None:
                        process.kill()
                    raise subprocess.TimeoutExpired(command, timeout)
                
                # Print status updates for long-running commands
                if time.time() - last_status_time >= status_interval:
                    elapsed_min = int(elapsed / 60)
                    print(f"⏳ {description} still running... ({elapsed_min} minutes elapsed)")
                    sys.stdout.flush()
                    last_status_time = time.time()
                
                # Process queued output
                try:
                    while True:
                        output_type, line = output_queue.get_nowait()
                        if output_type == 'stdout':
                            print(f"   {line}")
                            stdout_lines.append(line)
                        elif output_type == 'stderr':
                            # stderr often contains informational messages, not just errors
                            # Display it normally without special formatting
                            print(f"   {line}")
                            stderr_lines.append(line)
                        elif output_type == 'error':
                            # This is an actual error in the streaming process itself
                            print(f"   ⚠️  {line}", file=sys.stderr)
                        sys.stdout.flush()
                except Empty:
                    pass
                
                time.sleep(0.1)
            
            # Wait for threads to finish
            stdout_thread.join(timeout=5)
            stderr_thread.join(timeout=5)
            
            # Process any remaining output
            try:
                while True:
                    output_type, line = output_queue.get_nowait()
                    if output_type == 'stdout':
                        print(f"   {line}")
                        stdout_lines.append(line)
                    elif output_type == 'stderr':
                        # stderr often contains informational messages, not just errors
                        # Display it normally without special formatting
                        print(f"   {line}")
                        stderr_lines.append(line)
                    elif output_type == 'error':
                        # This is an actual error in the streaming process itself
                        print(f"   ⚠️  {line}", file=sys.stderr)
            except Empty:
                pass
            
            returncode = process.returncode
            stdout = '\n'.join(stdout_lines)
            stderr = '\n'.join(stderr_lines)
        else:
            # Fallback to original method if streaming disabled
            result = subprocess.run(
                command,
                cwd=cwd,
                capture_output=True,
                text=True,
                encoding='utf-8',
                errors='replace',
                timeout=timeout,
                env=env
            )
            returncode = result.returncode
            stdout = result.stdout
            stderr = result.stderr
            stdout_lines = stdout.split('\n') if stdout else []
            stderr_lines = stderr.split('\n') if stderr else []
        
        elapsed_time = time.time() - step_start_time
        elapsed_min = int(elapsed_time / 60)
        elapsed_sec = int(elapsed_time % 60)
        
        if returncode == 0:
            print(f"\n✅ {description} completed successfully")
            print(f"   Duration: {elapsed_min}m {elapsed_sec}s")
            print(f"   Finished at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
            sys.stdout.flush()
            return True, stdout, stderr
        else:
            print(f"\n❌ {description} failed with return code {returncode}")
            print(f"   Duration: {elapsed_min}m {elapsed_sec}s")
            print(f"   Failed at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
            if stderr:
                print(f"\n   Error output (last 50 lines):")
                error_lines = stderr_lines[-50:] if len(stderr_lines) > 50 else stderr_lines
                for line in error_lines:
                    print(f"   {line}")
            if stdout:
                # Show last few lines of stdout for context
                print(f"\n   Last output lines:")
                for line in stdout_lines[-10:]:
                    print(f"   {line}")
            sys.stdout.flush()
            return False, stdout, stderr
            
    except subprocess.TimeoutExpired:
        elapsed_time = time.time() - step_start_time
        elapsed_min = int(elapsed_time / 60)
        print(f"\n⏰ {description} timed out after {elapsed_min} minutes")
        print(f"   Timed out at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        sys.stdout.flush()
        return False, '\n'.join(stdout_lines), "Timeout after 1 hour"
    except Exception as e:
        elapsed_time = time.time() - step_start_time
        print(f"\n❌ Error running {description}: {e}")
        print(f"   Error type: {type(e).__name__}")
        print(f"   Error occurred at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"\n   Full traceback:")
        traceback.print_exc()
        sys.stdout.flush()
        return False, '\n'.join(stdout_lines), f"{type(e).__name__}: {str(e)}\n{traceback.format_exc()}"


def step_1_run_scrapers(stats):
    """Step 1: Run all scrapers"""
    stats.start_step('scraping')
    print("\n" + "="*80)
    print("STEP 1: RUNNING SCRAPERS")
    print("="*80)
    print(f"   This step will run all scrapers and may take a while...")
    print(f"   You'll see real-time output from each scraper as it runs.")
    sys.stdout.flush()
    
    scraper_script = os.path.join(project_root, 'scripts', 'scrapers', 'run_all_scrapers.py')
    command = [sys.executable, scraper_script]
    
    success, stdout, stderr = run_command(command, "Running all scrapers", stream_output_enabled=True)
    
    # Parse output to get statistics
    total_entries = 0
    scrapers_run = 0
    successful_scrapers = 0
    failed_scrapers = 0
    
    if success:
        # Try to extract statistics from output
        lines = stdout.split('\n')
        for line in lines:
            if 'Entries scraped:' in line:
                try:
                    count = int(line.split('Entries scraped:')[1].strip().split()[0])
                    total_entries += count
                    scrapers_run += 1
                except:
                    pass
            elif 'completed successfully' in line.lower():
                successful_scrapers += 1
            elif 'failed' in line.lower() or 'timed out' in line.lower():
                failed_scrapers += 1
    
    step_duration = stats.get_step_duration('scraping')
    step_duration_min = int(step_duration / 60)
    step_duration_sec = int(step_duration % 60)
    
    print(f"\n📊 Step 1 Summary:")
    print(f"   Status: {'✅ Success' if success else '❌ Failed'}")
    print(f"   Duration: {step_duration_min}m {step_duration_sec}s")
    print(f"   Scrapers run: {scrapers_run}")
    print(f"   Successful: {successful_scrapers}")
    if failed_scrapers > 0:
        print(f"   Failed: {failed_scrapers}")
    print(f"   Total entries scraped: {total_entries}")
    sys.stdout.flush()
    
    stats.add_step('scraping', 'success' if success else 'failed',
                   scrapers_run=scrapers_run,
                   successful_scrapers=successful_scrapers,
                   failed_scrapers=failed_scrapers,
                   total_entries=total_entries,
                   duration=step_duration,
                   error=stderr if not success else None)
    
    return success


def step_2_check_duplicates(stats):
    """Step 2: Check duplicates in raw JSON files"""
    stats.start_step('duplicate_check')
    print("\n" + "="*80)
    print("STEP 2: CHECKING DUPLICATES IN RAW JSON")
    print("="*80)
    sys.stdout.flush()
    
    duplicate_script = os.path.join(project_root, 'scripts', 'data', 'check_duplicate_entries.py')
    command = [sys.executable, duplicate_script]
    
    success, stdout, stderr = run_command(command, "Checking duplicates in raw JSON files", stream_output_enabled=True)
    
    # Parse output to get statistics
    files_processed = 0
    total_entries = 0
    duplicates_removed = 0
    
    if success:
        lines = stdout.split('\n')
        for line in lines:
            if 'Total entries processed:' in line:
                try:
                    total_entries = int(line.split('Total entries processed:')[1].strip())
                except:
                    pass
            elif 'Duplicates removed:' in line:
                try:
                    duplicates_removed = int(line.split('Duplicates removed:')[1].strip())
                except:
                    pass
            elif 'Found' in line and 'file(s) to process' in line:
                try:
                    files_processed = int(line.split('Found')[1].split('file(s)')[0].strip())
                except:
                    pass
    
    step_duration = stats.get_step_duration('duplicate_check')
    step_duration_min = int(step_duration / 60)
    step_duration_sec = int(step_duration % 60)
    
    print(f"\n📊 Step 2 Summary:")
    print(f"   Status: {'✅ Success' if success else '❌ Failed'}")
    print(f"   Duration: {step_duration_min}m {step_duration_sec}s")
    print(f"   Files processed: {files_processed}")
    print(f"   Total entries: {total_entries}")
    print(f"   Duplicates removed: {duplicates_removed}")
    sys.stdout.flush()
    
    stats.add_step('duplicate_check', 'success' if success else 'failed',
                   files_processed=files_processed,
                   total_entries=total_entries,
                   duplicates_removed=duplicates_removed,
                   duration=step_duration,
                   error=stderr if not success else None)
    
    return success


def step_3_standardize(stats):
    """Step 3: Standardize JSON files"""
    stats.start_step('standardization')
    print("\n" + "="*80)
    print("STEP 3: STANDARDIZING DATA")
    print("="*80)
    sys.stdout.flush()
    
    standardize_script = os.path.join(project_root, 'scripts', 'data', 'standardize_json.py')
    command = [sys.executable, standardize_script]
    
    success, stdout, stderr = run_command(command, "Standardizing JSON files", stream_output_enabled=True)
    
    # Parse output to get statistics
    files_processed = 0
    
    if success:
        lines = stdout.split('\n')
        for line in lines:
            if 'Found' in line and 'JSON files to standardize' in line:
                try:
                    files_processed = int(line.split('Found')[1].split('JSON files')[0].strip())
                except:
                    pass
    
    step_duration = stats.get_step_duration('standardization')
    step_duration_min = int(step_duration / 60)
    step_duration_sec = int(step_duration % 60)
    
    print(f"\n📊 Step 3 Summary:")
    print(f"   Status: {'✅ Success' if success else '❌ Failed'}")
    print(f"   Duration: {step_duration_min}m {step_duration_sec}s")
    print(f"   Files processed: {files_processed}")
    sys.stdout.flush()
    
    stats.add_step('standardization', 'success' if success else 'failed',
                   files_processed=files_processed,
                   duration=step_duration,
                   error=stderr if not success else None)
    
    return success


def step_5_drop_data(stats, app):
    """Step 5: Drop bike data from database"""
    stats.start_step('drop_data')
    print("\n" + "="*80)
    print("STEP 5: DROPPING BIKE DATA")
    print("="*80)
    print(f"   ⚠️  This will delete all existing bike data from the database!")
    sys.stdout.flush()
    
    drop_script = os.path.join(project_root, 'scripts', 'db', 'drop_bike_data.py')
    command = [sys.executable, drop_script, '--force']
    
    success, stdout, stderr = run_command(command, "Dropping bike data from database", stream_output_enabled=True)
    
    # Parse output to get statistics
    bikes_deleted = 0
    listings_deleted = 0
    
    if success:
        lines = stdout.split('\n')
        for line in lines:
            if 'Deleted' in line and 'bikes' in line:
                try:
                    bikes_deleted = int(line.split('Deleted')[1].split('bikes')[0].strip())
                except:
                    pass
            elif 'Deleted' in line and 'listings' in line:
                try:
                    listings_deleted = int(line.split('Deleted')[1].split('listings')[0].strip())
                except:
                    pass
    
    step_duration = stats.get_step_duration('drop_data')
    step_duration_min = int(step_duration / 60)
    step_duration_sec = int(step_duration % 60)
    
    print(f"\n📊 Step 5 Summary:")
    print(f"   Status: {'✅ Success' if success else '❌ Failed'}")
    print(f"   Duration: {step_duration_min}m {step_duration_sec}s")
    print(f"   Bikes deleted: {bikes_deleted}")
    print(f"   Listings deleted: {listings_deleted}")
    sys.stdout.flush()
    
    stats.add_step('drop_data', 'success' if success else 'failed',
                   bikes_deleted=bikes_deleted,
                   listings_deleted=listings_deleted,
                   duration=step_duration,
                   error=stderr if not success else None)
    
    return success


def step_6_migrate(stats, app):
    """Step 6: Migrate data to database"""
    stats.start_step('migration')
    print("\n" + "="*80)
    print("STEP 6: MIGRATING DATA TO DATABASE")
    print("="*80)
    print(f"   This step may take a while depending on the amount of data...")
    sys.stdout.flush()
    
    migrate_script = os.path.join(project_root, 'scripts', 'db', 'migrate_to_mysql.py')
    command = [sys.executable, migrate_script, '--force']
    
    success, stdout, stderr = run_command(command, "Migrating data to database", stream_output_enabled=True)
    
    # Parse output and get database statistics
    bikes_added = 0
    bikes_skipped = 0
    brands_count = 0
    sources_count = 0
    
    if success:
        # Get actual counts from database
        try:
            with app.app_context():
                bikes_added = Bike.query.count()
                brands_count = Brand.query.count()
                sources_count = Source.query.count()
        except Exception as e:
            print(f"   ⚠️  Warning: Could not query database counts: {e}")
        
        # Try to parse skipped count from output
        lines = stdout.split('\n')
        for line in lines:
            if 'Bikes skipped' in line or 'skipped (duplicates)' in line:
                try:
                    bikes_skipped = int(line.split('skipped')[0].split()[-1])
                except:
                    pass
    
    step_duration = stats.get_step_duration('migration')
    step_duration_min = int(step_duration / 60)
    step_duration_sec = int(step_duration % 60)
    
    print(f"\n📊 Step 6 Summary:")
    print(f"   Status: {'✅ Success' if success else '❌ Failed'}")
    print(f"   Duration: {step_duration_min}m {step_duration_sec}s")
    print(f"   Bikes added: {bikes_added}")
    if bikes_skipped > 0:
        print(f"   Bikes skipped (duplicates): {bikes_skipped}")
    print(f"   Brands in database: {brands_count}")
    print(f"   Sources in database: {sources_count}")
    sys.stdout.flush()
    
    stats.add_step('migration', 'success' if success else 'failed',
                   bikes_added=bikes_added,
                   bikes_skipped=bikes_skipped,
                   brands_count=brands_count,
                   sources_count=sources_count,
                   duration=step_duration,
                   error=stderr if not success else None)
    
    return success


def main():
    """Main pipeline execution"""
    import argparse
    
    parser = argparse.ArgumentParser(description='Run full data pipeline')
    parser.add_argument('--skip-scrapers', action='store_true', 
                       help='Skip scraping step (use existing raw data)')
    parser.add_argument('--dry-run', action='store_true',
                       help='Dry run mode (does not modify data)')
    
    args = parser.parse_args()
    
    # Load environment variables
    load_dotenv(override=True)
    
    # Create Flask app
    app = create_app()
    
    print("="*80)
    print("🚀 EMTB DATA PIPELINE")
    print("="*80)
    print(f"\nStarted at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"Project root: {project_root}")
    
    if args.dry_run:
        print("\n🔍 DRY RUN MODE - No data will be modified")
    
    if args.skip_scrapers:
        print("\n⏭️  Skipping scraping step (using existing data)")
    
    # Initialize statistics
    stats = PipelineStats()
    
    # Track overall success
    pipeline_success = True
    error_message = None
    
    try:
        # Step 0: Clear ChromeDriver cache (only if running scrapers)
        if not args.skip_scrapers:
            print(f"\n{'='*80}")
            print(f"🔄 Starting Step 0: Clearing ChromeDriver Cache")
            print(f"{'='*80}")
            sys.stdout.flush()
            try:
                clear_chromedriver_cache()
                print("✅ ChromeDriver cache cleared successfully")
                sys.stdout.flush()
            except Exception as e:
                print(f"⚠️  Warning: Could not clear ChromeDriver cache: {e}")
                print("   Continuing anyway...")
                sys.stdout.flush()
        
        # Step 1: Run scrapers
        if not args.skip_scrapers:
            print(f"\n{'='*80}")
            print(f"🔄 Starting Step 1/6: Running Scrapers")
            print(f"{'='*80}")
            sys.stdout.flush()
            if not step_1_run_scrapers(stats):
                pipeline_success = False
                error_message = "Scraping failed - check output above for details"
                raise Exception("Pipeline stopped at scraping step")
        else:
            stats.add_step('scraping', 'skipped')
            print(f"\n⏭️  Step 1/6: Scraping skipped (using existing data)")
            sys.stdout.flush()
        
        # Step 2: Check duplicates
        print(f"\n{'='*80}")
        print(f"🔄 Starting Step 2/6: Checking Duplicates")
        print(f"{'='*80}")
        sys.stdout.flush()
        if not step_2_check_duplicates(stats):
            pipeline_success = False
            error_message = "Duplicate check failed - check output above for details"
            raise Exception("Pipeline stopped at duplicate check step")
        
        # Step 3: Standardize
        print(f"\n{'='*80}")
        print(f"🔄 Starting Step 3/6: Standardizing Data")
        print(f"{'='*80}")
        sys.stdout.flush()
        if not step_3_standardize(stats):
            pipeline_success = False
            error_message = "Standardization failed - check output above for details"
            raise Exception("Pipeline stopped at standardization step")
        
        # Step 4: Deduplicate (SKIPPED - duplicates already removed in raw stage)
        # No need to deduplicate standardized data since duplicates were removed in step 2
        stats.add_step('deduplication', 'skipped',
                      note='Duplicates already removed in raw JSON stage')
        print(f"\n⏭️  Step 4/6: Deduplication skipped (already done in Step 2)")
        sys.stdout.flush()
        
        # Step 5: Drop data (only if not dry-run)
        if not args.dry_run:
            print(f"\n{'='*80}")
            print(f"🔄 Starting Step 5/6: Dropping Bike Data")
            print(f"{'='*80}")
            sys.stdout.flush()
            if not step_5_drop_data(stats, app):
                pipeline_success = False
                error_message = "Drop data failed - check output above for details"
                raise Exception("Pipeline stopped at drop data step")
        else:
            stats.add_step('drop_data', 'skipped')
            print(f"\n⏭️  Step 5/6: Drop data skipped (dry-run mode)")
            sys.stdout.flush()
        
        # Step 6: Migrate (only if not dry-run)
        if not args.dry_run:
            print(f"\n{'='*80}")
            print(f"🔄 Starting Step 6/6: Migrating Data to Database")
            print(f"{'='*80}")
            sys.stdout.flush()
            if not step_6_migrate(stats, app):
                pipeline_success = False
                error_message = "Migration failed - check output above for details"
                raise Exception("Pipeline stopped at migration step")
        else:
            stats.add_step('migration', 'skipped')
            print(f"\n⏭️  Step 6/6: Migration skipped (dry-run mode)")
            sys.stdout.flush()
        
        # All steps completed
        duration = stats.get_duration()
        duration_min = int(duration / 60)
        duration_sec = int(duration % 60)
        
        print("\n" + "="*80)
        print("✅ PIPELINE COMPLETED SUCCESSFULLY")
        print("="*80)
        print(f"Total duration: {duration_min}m {duration_sec}s")
        print(f"Finished at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print("\n📊 Final Summary:")
        for step_name, step_data in stats.stats.items():
            status_icon = "✅" if step_data.get('status') == 'success' else "⏭️" if step_data.get('status') == 'skipped' else "❌"
            print(f"   {status_icon} {step_name}: {step_data.get('status', 'unknown')}")
        sys.stdout.flush()
        
        # Send success notification
        try:
            send_pipeline_notification(
                stats.to_dict(),
                duration,
                'success'
            )
        except Exception as e:
            print(f"\n⚠️  Warning: Could not send email notification: {e}")
        
    except Exception as e:
        pipeline_success = False
        error_message = str(e)
        duration = stats.get_duration()
        duration_min = int(duration / 60)
        duration_sec = int(duration % 60)
        
        print("\n" + "="*80)
        print("❌ PIPELINE FAILED")
        print("="*80)
        print(f"Error: {error_message}")
        print(f"Error type: {type(e).__name__}")
        print(f"Duration: {duration_min}m {duration_sec}s")
        print(f"Failed at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"\nFull traceback:")
        traceback.print_exc()
        print(f"\n📊 Pipeline Status at Failure:")
        for step_name, step_data in stats.stats.items():
            status_icon = "✅" if step_data.get('status') == 'success' else "⏭️" if step_data.get('status') == 'skipped' else "❌"
            print(f"   {status_icon} {step_name}: {step_data.get('status', 'unknown')}")
        sys.stdout.flush()
        
        # Send failure notification
        try:
            send_pipeline_notification(
                stats.to_dict(),
                duration,
                'failed',
                error_message
            )
        except Exception as e:
            print(f"\n⚠️  Warning: Could not send email notification: {e}")
        
        sys.exit(1)
    
    print("\n" + "="*80)
    print("🎉 Pipeline execution complete!")
    print("="*80)


if __name__ == "__main__":
    main()

