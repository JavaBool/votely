import time
import threading
import utils # Import module to access updated global variable

# 1. Mock the sending function
def mock_send_email(i):
    print(f"[{time.time():.2f}] Task {i}: STARTED (Thread: {threading.current_thread().name})")
    time.sleep(2) # Simulate network delay
    print(f"[{time.time():.2f}] Task {i}: FINISHED")

if __name__ == "__main__":
    current_limit = utils.get_current_thread_limit()
    print(f"Original Configured Limit: {current_limit}")
    
    # 2. Set a low limit to force queuing
    print("Setting limit to 2 workers...")
    utils.update_email_thread_limit(2)
    print(f"New Configured Limit: {utils.get_current_thread_limit()}")
    # Note: utils.email_executor is now a NEW object
    print(f"Executor Max Workers: {utils.email_executor._max_workers}")
    
    # 3. Submit 5 tasks
    print("\nSubmitting 5 tasks simultaneously...")
    futures = []
    start_time = time.time()
    
    for i in range(1, 6):
        # We access the executor dynamically via the module
        f = utils.email_executor.submit(mock_send_email, i)
        futures.append(f)
        print(f"[{time.time():.2f}] Task {i}: SUBMITTED")

    # 4. Wait for all
    print("\nWaiting for completion...")
    for f in futures:
        f.result()
    
    end_time = time.time()
    print(f"\nAll tasks completed in {end_time - start_time:.2f} seconds.")
    
    # Reset limit to 5 to be nice
    utils.update_email_thread_limit(5)
