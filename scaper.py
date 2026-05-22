import os
import json
import time
import random
from urllib.parse import urlparse
from playwright.sync_api import sync_playwright

def run():
    input_path = "tm/main.json"
    output_dir = "public"
    json_output = os.path.join(output_dir, "data.json")
    m3u_output = os.path.join(output_dir, "playlist.m3u")

    if not os.path.exists(output_dir): 
        os.makedirs(output_dir)
    if not os.path.exists(input_path): 
        print("❌ Input file not found!")
        return

    with open(input_path, "r", encoding="utf-8") as f:
        source_channels = json.load(f)

    final_json_data = {"dev": "anirbansumon", "channels": []}
    m3u_content = "#EXTM3U\n"

    # বৈধ চ্যানেল ফিল্টার করা
    valid_channels = [item for item in source_channels if item.get("stream")]
    
    # 🚀 ফিক্স: 'SystemRandom' ব্যবহার করে গিটহাব রানারে ১০০% নিশ্চিতভাবে র‍্যান্ডমাইজ করা
    # এটি ওএসের ইন্টারনাল সিকিউরিটি ইঞ্জিন ব্যবহার করে প্রতিবার সম্পূর্ণ নতুন সিকোয়েন্স তৈরি করে
    crypt_random = random.SystemRandom()
    crypt_random.shuffle(valid_channels)
    print(f"🔀 Channels shuffled with SystemRandom. Total: {len(valid_channels)}")

    # হিউম্যান-লাইক ইউজার এজেন্ট লিস্ট
    user_agents = [
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:126.0) Gecko/20100101 Firefox/126.0",
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"
    ]

    for item in valid_channels:
        target_url = item.get("stream")
        channel_name = item.get("name", "Unknown")
        logo_url = item.get("logo", "")

        # স্ট্রিম সার্ভারের নাম বের করা
        server_domain = urlparse(target_url).netloc
        
        print(f"\n🖥️ Stream Server: {server_domain}")
        print(f"🚀 Processing: {channel_name}...")
        
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True, args=[
                "--disable-http2", 
                "--no-sandbox",
                "--disable-setuid-sandbox",
                "--disable-dev-shm-usage",
                "--disable-blink-features=AutomationControlled"
            ])
            
            # সিস্টেমের র্যান্ডম ইউজার এজেন্ট এবং স্ক্রিন সাইজ
            selected_ua = crypt_random.choice(user_agents)
            random_width = crypt_random.randint(1280, 1920)
            random_height = crypt_random.randint(720, 1080)
            
            context = browser.new_context(
                user_agent=selected_ua,
                viewport={"width": random_width, "height": random_height},
                bypass_csp=True
            )
            
            page = context.new_page()
            
            # ইমেজ, ফন্ট এবং সিএসেস ব্লক
            page.route("**/*", lambda route: route.abort() 
                       if route.request.resource_type in ["image", "font", "stylesheet"] 
                       else route.continue_())

            captured = {"url": None, "referer": target_url, "origin": "https://executeandship.com"}

            def handle_request(request):
                url = request.url
                if ".m3u8" in url.lower():
                    blacklist = ["chunk", "ad-", "telemetry", "google", "fb-", "log", "m3u8-video"]
                    if not any(x in url.lower() for x in blacklist):
                        if captured["url"] is None:
                            captured["url"] = url
                            captured["referer"] = request.headers.get("referer", target_url)
                            captured["origin"] = request.headers.get("origin", "https://executeandship.com")
                            print(f"✅ Found M3U8 for: {channel_name} [{server_domain}]")

            page.on("request", handle_request)

            try:
                page.goto(target_url, wait_until="networkidle", timeout=45000)
                
                for _ in range(30): 
                    if captured["url"]: 
                        break
                    page.wait_for_timeout(500)
                
                if not captured["url"]:
                    page.mouse.click(640, 360) 
                    for _ in range(14):
                        if captured["url"]: 
                            break
                        page.wait_for_timeout(500)

            except Exception as e:
                print(f"⚠️ Error: {channel_name} [{server_domain}] -> {str(e)[:50]}")

            if captured["url"]:
                final_json_data["channels"].append({
                    "name": channel_name, 
                    "url": captured["url"],
                    "referer": captured["referer"], 
                    "origin": captured["origin"]
                })
                
                m3u_content += f'#EXTINF:-1 tvg-logo="{logo_url}",{channel_name}\n'
                m3u_content += f'#EXTVLCOPT:http-referrer={captured["referer"]}\n'
                m3u_content += f'#EXTVLCOPT:http-origin={captured["origin"]}\n'
                m3u_content += f'#EXTVLCOPT:http-user-agent={selected_ua}\n'
                m3u_content += f'{captured["url"]}\n'
            else:
                print(f"❌ Failed to get link for: {channel_name} [{server_domain}]")
            
            page.close()
            context.close()
        
        # র্যান্ডম স্লিপ টাইম
        sleep_time = crypt_random.uniform(5, 10)
        print(f"⏳ Cooldown: Waiting for {sleep_time:.2f} seconds...")
        time.sleep(sleep_time)

    # ডাটা সেভ করা
    with open(json_output, "w", encoding="utf-8") as f: 
        json.dump(final_json_data, f, indent=4)
    with open(m3u_output, "w", encoding="utf-8") as f: 
        f.write(m3u_content)
        
    print(f"\n✨ Task Finished! Success: {len(final_json_data['channels'])}/{len(valid_channels)}")

if __name__ == "__main__":
    run()
