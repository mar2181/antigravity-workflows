"""
Facebook Marketing Automation Test
Runs through the basic workflows to verify the system is working
"""

import sys
import time
from facebook_marketer import FacebookMarketer


def test_basic_post():
    """Test creating a basic text post"""
    print("\n" + "=" * 70)
    print("TEST 1: Create a Simple Text Post")
    print("=" * 70)

    marketer = FacebookMarketer()
    marketer.launch_browser()

    try:
        message = "Test post from Facebook Marketing Automation Suite - Testing capabilities"
        success = marketer.post_text("juan", message)

        if success:
            print("\n[PASS] Text post test successful!")
            print("[INFO] Check Juan Elizondo RE/MAX Facebook page for the post")
            print("[INFO] You can delete it manually after verification")
        else:
            print("\n[FAIL] Text post test failed")

        return success

    finally:
        marketer.close_browser()


def test_page_navigation():
    """Test navigating to both pages"""
    print("\n" + "=" * 70)
    print("TEST 2: Page Navigation")
    print("=" * 70)

    marketer = FacebookMarketer()
    marketer.launch_browser()

    try:
        # Test Juan page
        print("\n[TEST] Navigating to Juan Elizondo RE/MAX...")
        success_juan = marketer.navigate_to_page("juan")

        if success_juan:
            print("[PASS] Juan page navigation successful")
        else:
            print("[FAIL] Juan page navigation failed")

        # Give time to see the page
        time.sleep(2)

        # Try Optimum page (may not be configured yet)
        print("\n[TEST] Attempting to navigate to Optimum page...")
        try:
            success_optimum = marketer.navigate_to_page("optimum")
            if success_optimum:
                print("[PASS] Optimum page navigation successful")
            else:
                print("[INFO] Optimum page not yet configured (expected)")
        except Exception as e:
            print(f"[INFO] Optimum page test skipped: {str(e)}")

        return success_juan

    finally:
        marketer.close_browser()


def test_insights():
    """Test accessing page insights"""
    print("\n" + "=" * 70)
    print("TEST 3: Access Page Insights")
    print("=" * 70)

    marketer = FacebookMarketer()
    marketer.launch_browser()

    try:
        success = marketer.get_page_insights("juan")

        if success:
            print("\n[PASS] Insights navigation successful")
            print("[INFO] Insights dashboard should be visible in the browser")
            print("[INFO] Close the browser when done reviewing")
        else:
            print("\n[FAIL] Insights navigation failed")

        # Keep browser open for user review
        print("\n[STEP] Press Enter to close the browser...")
        try:
            input()
        except:
            pass

        return success

    finally:
        marketer.close_browser()


def main():
    print("\n" + "=" * 70)
    print("FACEBOOK MARKETING AUTOMATION - TEST SUITE")
    print("=" * 70)
    print("\nThis will test the basic functionality of the automation suite.")
    print("Make sure you are ready to manually verify results on Facebook.\n")

    results = {
        "Page Navigation": False,
        "Text Post Creation": False,
        "Page Insights": False
    }

    # Test 1: Page Navigation (foundation)
    try:
        results["Page Navigation"] = test_page_navigation()
    except Exception as e:
        print(f"\n[ERROR] Page navigation test failed: {str(e)}")
        results["Page Navigation"] = False

    # Test 2: Text Post (core functionality)
    try:
        print("\n[WAIT] Continue to test post creation? (y/n): ", end="")
        response = input().lower().strip()
        if response == "y":
            results["Text Post Creation"] = test_basic_post()
    except Exception as e:
        print(f"\n[ERROR] Text post test failed: {str(e)}")
        results["Text Post Creation"] = False

    # Test 3: Insights (extended functionality)
    try:
        print("\n[WAIT] Continue to test page insights? (y/n): ", end="")
        response = input().lower().strip()
        if response == "y":
            results["Page Insights"] = test_insights()
    except Exception as e:
        print(f"\n[ERROR] Insights test failed: {str(e)}")
        results["Page Insights"] = False

    # Summary
    print("\n" + "=" * 70)
    print("TEST SUMMARY")
    print("=" * 70)

    for test_name, result in results.items():
        status = "[PASS]" if result else "[FAIL]"
        print(f"{status} {test_name}")

    passed = sum(1 for r in results.values() if r)
    total = len(results)

    print(f"\nResult: {passed}/{total} tests passed")

    if passed == total:
        print("\n[OK] All tests passed! The automation suite is ready to use.")
        print("\nUsage examples:")
        print("  python facebook_marketer.py --action text --page juan --message 'Your message here'")
        print("  python facebook_marketer.py --action image --page juan --message 'Caption' --media /path/to/image.jpg")
        print("  python facebook_marketer.py --action video --page juan --message 'Caption' --media /path/to/video.mp4")
        print("  python facebook_marketer.py --action insights --page juan")
        return 0
    else:
        print("\n[WARNING] Some tests failed. Check the output above for details.")
        print("[INFO] Common issues:")
        print("  - Selectors may have changed (Facebook updates UI frequently)")
        print("  - Session may be expired (run save_facebook_auth_mario.py to refresh)")
        print("  - Browser display issues (ensure headless=false in config)")
        return 1


if __name__ == "__main__":
    sys.exit(main())
