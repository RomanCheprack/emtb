#!/usr/bin/env python3
"""
Script to run all scrapers and save their output to data/scraped_raw_data/
"""

import os
import sys
import subprocess
import time
import json
import logging
import argparse
from datetime import datetime
from pathlib import Path
from threading import Thread

def stream_output(pipe, logger, prefix=""):
    """Stream output from a pipe in real-time, handling UTF-8 encoding"""
    try:
        # Read binary data and decode manually for better control
        buffer = b''
        while True:
            chunk = pipe.read(1024)  # Read in chunks
            if not chunk:  # EOF
                # Process any remaining buffer
                if buffer:
                    try:
                        line = buffer.decode('utf-8', errors='replace').rstrip()
                        if line:
                            print(f"{prefix}{line}", flush=True)
                            logger.info(f"{prefix}{line}")
                    except Exception:
                        pass
                break
            
            buffer += chunk
            
            # Process complete lines
            while b'\n' in buffer:
                line_bytes, buffer = buffer.split(b'\n', 1)
                try:
                    line = line_bytes.decode('utf-8', errors='replace').rstrip()
                    if line:
                        try:
                            print(f"{prefix}{line}", flush=True)
                            logger.info(f"{prefix}{line}")
                        except (UnicodeEncodeError, UnicodeDecodeError):
                            # Fallback: replace problematic characters
                            safe_line = line.encode('utf-8', errors='replace').decode('utf-8', errors='replace')
                            print(f"{prefix}{safe_line}", flush=True)
                            logger.info(f"{prefix}{safe_line}")
                except Exception as e:
                    # Skip lines that can't be decoded
                    logger.warning(f"Error decoding line: {e}, skipping...")
                    continue
        pipe.close()
    except Exception as e:
        logger.error(f"Error streaming output: {e}")

def run_scraper(scraper_path, output_dir, logger):
    """Run a single scraper and save output to the specified directory"""
    scraper_name = Path(scraper_path).stem
    start_time = time.time()
    start_datetime = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    print(f"\n{'='*50}")
    print(f"Running scraper: {scraper_name}")
    print(f"Started at: {start_datetime}")
    print(f"{'='*50}")
    logger.info(f"Starting scraper: {scraper_name} at {start_datetime}")
    
    # Change to the scrapers directory so relative imports work
    original_dir = os.getcwd()
    scrapers_dir = Path(scraper_path).parent
    os.chdir(scrapers_dir)
    
    result_info = {
        "name": scraper_name,
        "status": "unknown",
        "returncode": None,
        "elapsed_time": 0,
        "error": None,
        "stdout_lines": [],
        "stderr_lines": []
    }
    
    try:
        # Run the scraper with real-time output streaming
        # Increased timeout to 30 minutes (1800 seconds) as scrapers can take a long time
        # Set up environment with UTF-8 encoding
        env = os.environ.copy()
        env['PYTHONIOENCODING'] = 'utf-8'
        env['PYTHONUTF8'] = '1'  # Enable UTF-8 mode in Python 3.7+
        
        process = subprocess.Popen(
            [sys.executable, Path(scraper_path).name],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            bufsize=0,  # Unbuffered for real-time output
            env=env,
            cwd=scrapers_dir  # Explicitly set working directory
        )
        
        # Start threads to stream stdout and stderr in real-time
        stdout_thread = Thread(target=stream_output, args=(process.stdout, logger, f"[{scraper_name}] "))
        stderr_thread = Thread(target=stream_output, args=(process.stderr, logger, f"[{scraper_name}] ERROR: "))
        
        stdout_thread.daemon = True
        stderr_thread.daemon = True
        
        stdout_thread.start()
        stderr_thread.start()
        
        # Wait for process to complete with periodic status updates and timeout
        last_status_time = time.time()
        status_interval = 300  # Print status every 5 minutes
        timeout_seconds = 1800  # 30 minutes timeout
        
        while process.poll() is None:
            elapsed = time.time() - start_time
            
            # Check for timeout
            if elapsed >= timeout_seconds:
                process.terminate()
                time.sleep(2)
                if process.poll() is None:
                    process.kill()
                raise subprocess.TimeoutExpired(process.args, timeout_seconds)
            
            # Periodic status updates
            if time.time() - last_status_time >= status_interval:
                elapsed_min = int(elapsed / 60)
                print(f"⏳ {scraper_name} still running... ({elapsed_min} minutes elapsed)")
                logger.info(f"{scraper_name} still running after {elapsed_min} minutes")
                last_status_time = time.time()
            
            time.sleep(1)
        
        # Wait for threads to finish
        stdout_thread.join(timeout=5)
        stderr_thread.join(timeout=5)
        
        result_info["returncode"] = process.returncode
        elapsed_time = time.time() - start_time
        result_info["elapsed_time"] = elapsed_time
        
        if process.returncode == 0:
            elapsed_min = int(elapsed_time / 60)
            elapsed_sec = int(elapsed_time % 60)
            end_datetime = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            
            # Count entries in the output file
            scraper_to_file = {
                "cobra_full_site": "cobra_data.json",
                "ctc_full_site": "ctc_data.json",
                "cube_full_site": "cube_data.json",
                "giant_full_site": "giant_data.json",
                "matzman_full_site": "matzman_data.json",
                "motofan_full_site": "motofan_data.json",
                "motosport_full_site": "motosport_data.json",
                "pedalim_full_site": "pedalim_data.json",
                "recycles_full_site": "recycles_data.json",
                "rosen_full_site": "rosen_data.json",
            }
            output_filename = scraper_to_file.get(scraper_name, f"{scraper_name.replace('_full_site', '')}_data.json")
            output_file_path = output_dir / output_filename
            entry_count = count_json_entries(output_file_path)
            
            print(f"\n✅ {scraper_name} completed successfully")
            print(f"   Duration: {elapsed_min}m {elapsed_sec}s")
            print(f"   Finished at: {end_datetime}")
            if entry_count is not None:
                print(f"📊 Entries scraped: {entry_count}")
                result_info["entry_count"] = entry_count
            else:
                print(f"⚠️  Could not count entries in output file")
                result_info["entry_count"] = None
            print(f"📁 Data saved to {output_dir}")
            result_info["status"] = "success"
            logger.info(f"{scraper_name} completed successfully in {elapsed_min}m {elapsed_sec}s")
            if entry_count is not None:
                logger.info(f"{scraper_name} scraped {entry_count} entries")
        else:
            elapsed_min = int(elapsed_time / 60)
            elapsed_sec = int(elapsed_time % 60)
            print(f"\n❌ {scraper_name} failed with return code {process.returncode}")
            print(f"   Duration: {elapsed_min}m {elapsed_sec}s")
            result_info["status"] = "failed"
            result_info["error"] = f"Return code: {process.returncode}"
            logger.error(f"{scraper_name} failed with return code {process.returncode} after {elapsed_min}m {elapsed_sec}s")
            
    except subprocess.TimeoutExpired:
        elapsed_time = time.time() - start_time
        elapsed_min = int(elapsed_time / 60)
        print(f"\n⏰ {scraper_name} timed out after 30 minutes")
        result_info["status"] = "timeout"
        result_info["elapsed_time"] = elapsed_time
        result_info["error"] = "Timeout after 30 minutes"
        logger.error(f"{scraper_name} timed out after {elapsed_min} minutes")
    except Exception as e:
        elapsed_time = time.time() - start_time
        print(f"\n❌ Error running {scraper_name}: {e}")
        result_info["status"] = "error"
        result_info["elapsed_time"] = elapsed_time
        result_info["error"] = str(e)
        logger.error(f"Error running {scraper_name}: {e}", exc_info=True)
    finally:
        # Change back to original directory
        os.chdir(original_dir)
    
    return result_info

def setup_logging(project_root):
    """Setup file logging"""
    logs_dir = project_root / "logs" / "scrapers"
    os.makedirs(logs_dir, exist_ok=True)
    
    log_filename = datetime.now().strftime("%Y-%m-%d_%H-%M-%S.log")
    log_file = logs_dir / log_filename
    
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler(log_file, encoding='utf-8'),
            logging.StreamHandler()
        ]
    )
    
    logger = logging.getLogger(__name__)
    logger.info(f"Logging to: {log_file}")
    return logger, log_file

def get_file_size(filepath):
    """Get file size in a human-readable format"""
    try:
        if os.path.exists(filepath):
            size = os.path.getsize(filepath)
            if size < 1024:
                return f"{size} B"
            elif size < 1024 * 1024:
                return f"{size / 1024:.1f} KB"
            else:
                return f"{size / (1024 * 1024):.1f} MB"
        return "N/A"
    except:
        return "N/A"

def count_json_entries(filepath):
    """Count the number of entries in a JSON file"""
    try:
        if os.path.exists(filepath):
            with open(filepath, 'r', encoding='utf-8') as f:
                data = json.load(f)
                if isinstance(data, list):
                    return len(data)
                elif isinstance(data, dict):
                    return 1
                return 0
        return None
    except json.JSONDecodeError:
        return None
    except Exception:
        return None

def filter_scrapers(scraper_files, only=None, skip=None, from_scraper=None):
    """
    Filter scraper files based on command-line arguments.
    
    Args:
        scraper_files: List of Path objects for scraper files
        only: List of normalized scraper names (already normalized, lowercase, no .py)
        skip: List of normalized scraper names (already normalized, lowercase, no .py)
        from_scraper: Normalized scraper name to start from (inclusive, already normalized)
    
    Returns:
        Filtered list of scraper files
    """
    # Convert to list of tuples (normalized_name, path) for easier filtering
    scrapers = [(f.stem.lower(), f) for f in scraper_files]
    
    # Filter by --only
    if only:
        only_set = set(only)  # Already normalized
        scrapers = [(name, path) for name, path in scrapers if name in only_set]
        if not scrapers:
            print(f"⚠️  Warning: No scrapers found matching --only: {only}")
            print(f"   Available scrapers: {[f.stem for f in scraper_files]}")
    
    # Filter by --skip
    if skip:
        skip_set = set(skip)  # Already normalized
        scrapers = [(name, path) for name, path in scrapers if name not in skip_set]
    
    # Filter by --from
    if from_scraper:
        from_name = from_scraper  # Already normalized
        found = False
        filtered = []
        for name, path in scrapers:
            if not found and name == from_name:
                found = True
            if found:
                filtered.append((name, path))
        if not found:
            print(f"⚠️  Warning: Scraper '{from_scraper}' not found for --from option")
            print(f"   Available scrapers: {[f.stem for f in scraper_files]}")
        scrapers = filtered
    
    # Return just the paths
    return [path for _, path in scrapers]

def normalize_scraper_name(name):
    """Normalize scraper name by removing @, .py extension, and converting to lowercase"""
    name = name.strip()
    # Remove @ symbol if present
    if name.startswith('@'):
        name = name[1:]
    # Remove .py extension if present
    if name.endswith('.py'):
        name = name[:-3]
    return name.lower()

def main():
    """Run all scrapers"""
    # Parse command-line arguments
    parser = argparse.ArgumentParser(
        description='Run scrapers with optional filtering',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python run_all_scrapers.py                          # Run all scrapers
  python run_all_scrapers.py --only matzman_full_site # Run only matzman_full_site
  python run_all_scrapers.py --skip cobra_full_site   # Skip cobra_full_site
  python run_all_scrapers.py --from matzman_full_site # Start from matzman_full_site (inclusive)
        """
    )
    parser.add_argument('--only', nargs='+', help='Run only these scrapers (by name, without .py)')
    parser.add_argument('--skip', nargs='+', help='Skip these scrapers (by name, without .py)')
    parser.add_argument('--from', dest='from_scraper', help='Start from this scraper (inclusive, by name, without .py)')
    
    args = parser.parse_args()
    
    # Normalize scraper names in arguments
    only_list = [normalize_scraper_name(name) for name in (args.only or [])]
    skip_list = [normalize_scraper_name(name) for name in (args.skip or [])]
    from_scraper = normalize_scraper_name(args.from_scraper) if args.from_scraper else None
    
    overall_start_time = time.time()
    overall_start_datetime = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    # Set UTF-8 encoding for all subprocesses to handle emojis and Unicode
    os.environ['PYTHONIOENCODING'] = 'utf-8'
    
    # Get the project root directory (two levels above scripts/)
    project_root = Path(__file__).resolve().parents[2]
    scrapers_dir = project_root / "data" / "scrapers"
    output_dir = project_root / "data" / "scraped_raw_data"
    
    # Setup logging
    logger, log_file = setup_logging(project_root)
    
    print(f"\n{'='*70}")
    print(f"SCRAPER ORCHESTRATOR")
    print(f"{'='*70}")
    print(f"Started at: {overall_start_datetime}")
    print(f"Looking for scrapers in: {scrapers_dir}")
    print(f"Output directory: {output_dir}")
    print(f"Log file: {log_file}")
    if only_list or skip_list or from_scraper:
        print(f"\nFiltering options:")
        if only_list:
            print(f"  --only: {only_list}")
        if skip_list:
            print(f"  --skip: {skip_list}")
        if from_scraper:
            print(f"  --from: {from_scraper}")
    print(f"{'='*70}\n")
    
    logger.info(f"Scraper orchestrator started at {overall_start_datetime}")
    logger.info(f"Scrapers directory: {scrapers_dir}")
    logger.info(f"Output directory: {output_dir}")
    if only_list:
        logger.info(f"Filtering: --only {only_list}")
    if skip_list:
        logger.info(f"Filtering: --skip {skip_list}")
    if from_scraper:
        logger.info(f"Filtering: --from {from_scraper}")
    
    # Find all Python files in the scrapers directory
    all_scraper_files = list(scrapers_dir.glob("*.py"))
    
    if not all_scraper_files:
        print("❌ No scraper files found!")
        logger.error("No scraper files found!")
        return
    
    # Filter scrapers based on command-line arguments
    scraper_files = filter_scrapers(all_scraper_files, only=only_list, skip=skip_list, from_scraper=from_scraper)
    
    if not scraper_files:
        print("❌ No scrapers to run after filtering!")
        logger.error("No scrapers to run after filtering!")
        return
    
    print(f"Found {len(all_scraper_files)} total scrapers, {len(scraper_files)} to run:")
    for scraper in scraper_files:
        print(f"  ✓ {scraper.name}")
    if len(scraper_files) < len(all_scraper_files):
        skipped = set(f.name for f in all_scraper_files) - set(f.name for f in scraper_files)
        print(f"\nSkipped {len(skipped)} scrapers:")
        for scraper_name in sorted(skipped):
            print(f"  ⊘ {scraper_name}")
    
    # Create output directory
    os.makedirs(output_dir, exist_ok=True)
    
    # Run each scraper and collect results
    results = []
    for i, scraper_file in enumerate(scraper_files, 1):
        print(f"\n[{i}/{len(scraper_files)}] ", end="")
        result = run_scraper(scraper_file, output_dir, logger)
        results.append(result)
        time.sleep(2)  # Small delay between scrapers
    
    # Calculate overall statistics
    overall_elapsed = time.time() - overall_start_time
    overall_elapsed_min = int(overall_elapsed / 60)
    overall_elapsed_sec = int(overall_elapsed % 60)
    overall_end_datetime = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    # Final summary
    print(f"\n{'='*70}")
    print("FINAL SUMMARY")
    print(f"{'='*70}")
    print(f"Started: {overall_start_datetime}")
    print(f"Finished: {overall_end_datetime}")
    print(f"Total duration: {overall_elapsed_min}m {overall_elapsed_sec}s")
    print(f"\nResults:")
    
    success_count = sum(1 for r in results if r["status"] == "success")
    failed_count = sum(1 for r in results if r["status"] == "failed")
    timeout_count = sum(1 for r in results if r["status"] == "timeout")
    error_count = sum(1 for r in results if r["status"] == "error")
    
    print(f"  ✅ Successful: {success_count}/{len(results)}")
    if failed_count > 0:
        print(f"  ❌ Failed: {failed_count}")
    if timeout_count > 0:
        print(f"  ⏰ Timed out: {timeout_count}")
    if error_count > 0:
        print(f"  ⚠️  Errors: {error_count}")
    
    print(f"\nDetailed Results:")
    print(f"{'Scraper':<25} {'Status':<12} {'Duration':<15} {'Entries':<10} {'File Size':<15}")
    print("-" * 80)
    
    for result in results:
        scraper_name = result["name"]
        status_icon = {
            "success": "✅",
            "failed": "❌",
            "timeout": "⏰",
            "error": "⚠️"
        }.get(result["status"], "❓")
        
        elapsed = result["elapsed_time"]
        elapsed_str = f"{int(elapsed/60)}m {int(elapsed%60)}s" if elapsed > 0 else "N/A"
        
        # Map scraper name to output file name (scrapers create files like cobra_data.json)
        scraper_to_file = {
            "cobra_full_site": "cobra_data.json",
            "ctc_full_site": "ctc_data.json",
            "cube_full_site": "cube_data.json",
            "giant_full_site": "giant_data.json",
            "matzman_full_site": "matzman_data.json",
            "motofan_full_site": "motofan_data.json",
            "motosport_full_site": "motosport_data.json",
            "pedalim_full_site": "pedalim_data.json",
            "recycles_full_site": "recycles_data.json",
            "rosen_full_site": "rosen_data.json",
        }
        output_filename = scraper_to_file.get(scraper_name, f"{scraper_name.replace('_full_site', '')}_data.json")
        output_file = output_dir / output_filename
        file_size = get_file_size(output_file)
        
        # Get entry count (from result or count from file)
        entry_count = result.get("entry_count")
        if entry_count is None and result["status"] == "success":
            entry_count = count_json_entries(output_file)
        entry_count_str = str(entry_count) if entry_count is not None else "N/A"
        
        status_display = f"{status_icon} {result['status']}"
        print(f"{scraper_name:<25} {status_display:<12} {elapsed_str:<15} {entry_count_str:<10} {file_size:<15}")
        
        if result["error"]:
            print(f"  └─ Error: {result['error']}")
    
    print(f"\n📁 Output files location: {output_dir}")
    print(f"📝 Log file: {log_file}")
    print(f"{'='*70}\n")
    
    logger.info(f"Orchestrator completed. Success: {success_count}/{len(results)}, Total time: {overall_elapsed_min}m {overall_elapsed_sec}s")
    
    # Exit with error code if any scrapers failed
    if failed_count > 0 or timeout_count > 0 or error_count > 0:
        sys.exit(1)

if __name__ == "__main__":
    main() 