import os
import json
import requests
import random
import time
from urllib.parse import urlparse
from playwright.sync_api import sync_playwright

def check_status(url, ref, org):
    try:
        headers = {"Referer": ref, "Origin": org, "User-Agent": "Mozilla/5.0"}
        r = requests.head(url, headers=headers, timeout=5)
        return "✅ LIVE" if r.status_code == 200 else f"⚠️ {r.status_code}"
    except:
        return "❌ DOWN"

def run():
    input_file, out_dir = "tm/main.json", "public"
    os.makedirs(out_dir, exist_ok=True)
    
    if not os.path.exists(input_file):
        print("❌ Error: tm/main.json ফাইলটি পাওয়া যায়নি!")
        return

    with open(input_file, "r", encoding="utf-8") as f:
        channels = json.load(f)

    # ওএসের সিকিউরিটি ইঞ্জিন (SystemRandom) দিয়ে ১০০% র‍্যান্ডমাইজ করা
    crypt_random = random.SystemRandom()
    crypt_random.shuffle(channels)

    total_channels = len(channels)
    print(f"🔀 চ্যানেলগুলো র‍্যান্ডমলি সাজানো হয়েছে যেন সার্ভার ব্লক না করে।")
    print(f"🚀 স্ক্র্যাপিং শুরু হচ্ছে... মোট চ্যানেল: {total_channels}\n" + "="*50)

    results = {"dev": "anirbansumon", "channels": []}
    m3u = "#EXTM3U\n"
    success_count = 0

    with sync_playwright() as p:
        # মেইন ব্রাউজার ইঞ্জিন চালু করা
        browser = p.chromium.launch(headless=True, args=["--no-sandbox", "--disable-gpu"])

        for index, item in enumerate(channels, 1):
            name = item.get("name", "Unknown")
            target = item.get("stream")
            
            # প্রগ্রেস মেসেজ
            print(f"[{index}/{total_channels}] ⏳ Processing: {name}...", end="\r", flush=True)

            if not target:
                print(f"[{index}/{total_channels}] ❌ {name}: No Source URL found.       ")
                continue

            # স্ট্রিম ইউআরএল থেকে মেইন ডোমেইন/সার্ভার আলাদা করা
            server_domain = urlparse(target).netloc
            print(f"\n🖥️ Stream Server: {server_domain}")

            # প্রতিটা চ্যানেলের জন্য সম্পূর্ণ নতুন ও ফ্রেশ উইন্ডো (Context) খোলা
            context = browser.new_context(user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36")
            page = context.new_page()
            
            # ফাস্ট লোডিংয়ের জন্য অপ্রয়োজনীয় রিসোর্স ব্লক
            page.route("**/*.{png,jpg,jpeg,gif,css,woff}", lambda r: r.abort())

            links = []
            page.on("request", lambda req: links.append({
                "url": req.url, 
                "ref": req.headers.get("referer", target),
                "org": req.headers.get("origin", "https://executeandship.com")
            }) if ".m3u8" in req.url.lower() and "chunk" not in req.url.lower() else None)

            try:
                page.goto(target, wait_until="domcontentloaded", timeout=45000)
                
                page.wait_for_timeout(3000)
                try:
                    page.mouse.click(100, 100) # প্লেয়ারের উপরে ক্লিক ট্রিপার
                except: pass
                
                for _ in range(10):
                    if any(".m3u8" in l["url"] for l in links): break
                    page.wait_for_timeout(1000)

            except Exception as e:
                pass

            # MASTER প্লেলিস্টকে প্রায়োরিটি দেওয়া
            final = next((l for l in links if "master" in l["url"].lower()), None)
            if not final and links:
                final = links[0]

            # 🚀 ফিক্স লজিক: লিঙ্ক পাওয়ার পর সেটির লাইভ স্ট্যাটাস চেক করা হচ্ছে
            if final:
                status = check_status(final["url"], final["ref"], final["org"])
                
                # 📌 শুধুমাত্র স্ট্যাটাস '✅ LIVE' হলেই প্লেলিস্ট এবং ডাটায় অ্যাড হবে
                if status == "✅ LIVE":
                    success_count += 1
                    results["channels"].append({
                        "name": name, 
                        "url": final["url"], 
                        "referer": final["ref"],
                        "origin": final["org"]
                    })
                    
                    m3u += f'#EXTINF:-1 tvg-logo="{item.get("logo","")}",{name}\n'
                    m3u += f'#EXTVLCOPT:http-referrer={final["ref"]}\n'
                    m3u += f'#EXTVLCOPT:http-origin={final["org"]}\n'
                    m3u += f'{final["url"]}\n'
                    
                    print(f"[{index}/{total_channels}] {status} | {name} [{server_domain}]")
                else:
                    # লিঙ্ক পাওয়া গেছে কিন্তু সার্ভার ৪০৪ বা অন্য এরর দিয়েছে (অর্থাৎ লাইভ নেই)
                    print(f"[{index}/{total_channels}] ❌ FAILED | {name} [{server_domain}] (Status: {status})")
            else:
                # পেজ থেকে কোনো লিঙ্কই খুঁজে পাওয়া যায়নি
                print(f"[{index}/{total_channels}] ❌ FAILED | {name} [{server_domain}] (No link found)")
            
            # কাজ শেষ হওয়া মাত্রই কারেন্ট পেজ এবং পুরো উইন্ডো ক্লোজ করে দেওয়া
            page.close()
            context.close()

            # ৪ থেকে ৮ সেকেন্ডের একটি ছোট র্যান্ডম বিরতি
            sleep_time = crypt_random.uniform(4, 8)
            time.sleep(sleep_time)

        # পুরো স্ক্র্যাপিং শেষে মেইন ব্রাউজার বন্ধ করা
        browser.close()

    # ডাটা সেভ
    with open(f"{out_dir}/data.json", "w", encoding="utf-8") as f:
        json.dump(results, f, indent=4)
    with open(f"{out_dir}/playlist.m3u", "w", encoding="utf-8") as f:
        f.write(m3u)

    print("="*50)
    print(f"✅ স্ক্র্যাপিং সম্পন্ন! সফল (লাইভ): {success_count} | ব্যর্থ/অফলাইন: {total_channels - success_count}")
    print(f"📁 ফাইল সেভ করা হয়েছে: {out_dir}/ ফোল্ডারে।")

if __name__ == "__main__":
    run()
