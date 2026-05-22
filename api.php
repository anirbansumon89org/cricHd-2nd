<?php
ob_start(); // আউটপুট বাফারিং শুরু যেন কোনো এরর ডাটা নষ্ট না করে
require __DIR__.'/admin/config.php'; 
require __DIR__.'/admin/db.php';

header('Content-Type: text/plain; charset=utf-8');

// MASTER_KEY চেক
if (!defined('MASTER_KEY')) { define('MASTER_KEY', 'ULTRA_PRIVATE_MASTER_987'); }

$key  = trim($_GET['license'] ?? '');
$sid  = trim($_GET['script_id'] ?? '');
$hwid = trim($_GET['hwid'] ?? ''); 
$ip   = $_SERVER['REMOTE_ADDR'];

if ($key === '' || $sid === '' || $hwid === '') {
    ob_clean(); die("access_denied");
}

// ১. লাইসেন্স ভ্যালিডেশন
$stmt = $db->prepare("SELECT l.*, s.script_code, s.script_version FROM licenses l JOIN scripts s ON l.script_id = s.script_id WHERE l.license_key = :key AND l.script_id = :sid LIMIT 1");
$stmt->execute([':key' => $key, ':sid' => $sid]);
$l = $stmt->fetch(PDO::FETCH_ASSOC);

if (!$l || $l['status'] == 0 || strtotime($l['expire_date']) < time()) { 
    ob_clean(); die("access_denied"); 
}

// ২. HWID বাইন্ডিং (স্টেবল লজিক)
$usage = $db->prepare("SELECT * FROM license_usage WHERE license_key = ? LIMIT 1");
$usage->execute([$key]);
$u = $usage->fetch();

if (!$u) {
    $db->prepare("INSERT INTO license_usage (license_key, hwid, first_active, last_ip) VALUES (?, ?, datetime('now'), ?)")->execute([$key, $hwid, $ip]);
} else {
    if ($u['hwid'] !== $hwid) { 
        ob_clean(); die("invalid_device"); 
    }
    $db->prepare("UPDATE license_usage SET last_ip = ? WHERE license_key = ?")->execute([$ip, $key]);
}

// ৩. এনক্রিপশন লজিক
$dynamicKey = hash('sha256', $key . $hwid . MASTER_KEY, true);
$iv = random_bytes(16);
$payload = json_encode(['code' => $l['script_code'], 'ver' => $l['script_version']]);

$enc = openssl_encrypt($payload, 'AES-256-CBC', $dynamicKey, OPENSSL_RAW_DATA, $iv);
$hmac = hash_hmac('sha256', $enc, $dynamicKey);

// রেসপন্স ক্লিনিং
$json_res = json_encode([
    'd'  => base64_encode($enc), 
    'iv' => base64_encode($iv), 
    'h'  => $hmac
]);

$response = base64_encode($json_res);

ob_clean(); // আগে কোনো অদৃশ্য আউটপুট থাকলে মুছে ফেলবে
echo $response;
exit;