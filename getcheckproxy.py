import os
import subprocess
import requests
from bs4 import BeautifulSoup
import re
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
from concurrent.futures import ThreadPoolExecutor
from requests.exceptions import RequestException
import time

# Proxy toplama fonksiyonları
def fetch_proxies_from_sslproxies():
    url = "https://www.sslproxies.org/"
    response = requests.get(url, allow_redirects=False)
    soup = BeautifulSoup(response.text, 'html.parser')
    proxies = []

    proxy_pattern = re.compile(r'^\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}:\d+$')

    for row in soup.find_all('tr'):
        cols = row.find_all('td')
        if len(cols) > 1:
            ip = cols[0].text
            port = cols[1].text
            proxy = f"{ip}:{port}"
            if proxy_pattern.match(proxy):
                proxies.append(proxy)

    return proxies

def fetch_proxies_from_geonode():
    chrome_options = Options()
    chrome_options.add_argument("--headless")
    chrome_options.add_argument("--disable-gpu")
    chrome_options.add_argument("--no-sandbox")

    driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=chrome_options)
    socks4_proxies = []
    socks5_proxies = []
    ssl_proxies = []
    http_proxies = []

    try:
        url = "https://geonode.com/free-proxy-list/"
        driver.get(url)

        while True:
            time.sleep(2)
            table = driver.find_element(By.CLASS_NAME, 'free-proxies-table')
            rows = table.find_elements(By.TAG_NAME, 'tr')
            for row in rows:
                cols = row.find_elements(By.TAG_NAME, 'td')
                if len(cols) > 3:
                    ip = cols[0].text.strip()
                    port = cols[1].text.strip()
                    protocol = cols[3].text.strip().lower()
                    proxy = f"{ip}:{port}"
                    proxy_pattern = re.compile(r'^\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}:\d+$')

                    if proxy_pattern.match(proxy):
                        if 'socks4' in protocol:
                            socks4_proxies.append(proxy)
                        elif 'socks5' in protocol:
                            socks5_proxies.append(proxy)
                        elif 'https' in protocol:
                            ssl_proxies.append(proxy)
                        elif 'http' in protocol:
                            http_proxies.append(proxy)

            driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
            time.sleep(1)

            try:
                next_button = driver.find_element(By.XPATH, "//button[contains(text(), 'Next') and not(@disabled)]")
                driver.execute_script("arguments[0].click();", next_button)
            except Exception:
                break

    finally:
        driver.quit()

    return socks4_proxies, socks5_proxies, ssl_proxies, http_proxies

def fetch_proxies_from_socksproxy():
    url = "https://www.socks-proxy.net/"
    response = requests.get(url,allow_redirects=False)
    soup = BeautifulSoup(response.text, 'html.parser')
    proxies = []

    proxy_pattern = re.compile(r'^\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}:\d+$')

    for row in soup.find_all('tr'):
        cols = row.find_all('td')
        if len(cols) > 1:
            ip = cols[0].text
            port = cols[1].text
            proxy = f"{ip}:{port}"
            if proxy_pattern.match(proxy):
                proxies.append(proxy)

    return proxies

def fetch_proxies_from_proxyscrape():
    url = "https://api.proxyscrape.com/v3/free-proxy-list/get?request=displayproxies&proxy_format=protocolipport&format=text"
    response = requests.get(url, allow_redirects=False)
    socks4_proxies = []
    socks5_proxies = []
    ssl_proxies = []
    http_proxies = []

    if response.status_code == 200:
        proxies = response.text.splitlines()
        for proxy in proxies:
            if proxy.startswith('socks4://'):
                socks4_proxies.append(proxy.replace('socks4://', ''))
            elif proxy.startswith('socks5://'):
                socks5_proxies.append(proxy.replace('socks5://', ''))
            elif proxy.startswith('https://'):
                ssl_proxies.append(proxy.replace('https://', ''))
            elif proxy.startswith('http://'):
                http_proxies.append(proxy.replace('http://', ''))

    return socks4_proxies, socks5_proxies, ssl_proxies, http_proxies

def fetch_proxies_from_advanced_name():
    base_url = "https://advanced.name/freeproxy?page="
    page = 1
    socks4_proxies = []
    socks5_proxies = []
    ssl_proxies = []
    http_proxies = []

    while True:
        url = base_url + str(page)
        response = requests.get(url,allow_redirects=False)

        if response.status_code != 200:
            print(f"Hata: Sayfa {page} yüklenemedi. Status code: {response.status_code}")
            break

        soup = BeautifulSoup(response.text, 'html.parser')

        table = soup.find('table', {'id': 'table_proxies'})
        if not table:
            print(f"Tablo bulunamadı sayfa {page}.")
            break

        for row in table.find('tbody').find_all('tr'):
            cols = row.find_all('td')
            if len(cols) < 4:
                continue

            ip = cols[1].text.strip()
            port = cols[2].text.strip()
            protocols = [link.text.strip().lower() for link in cols[3].find_all('a')]
            proxy = f"{ip}:{port}"

            if 'socks4' in protocols:
                socks4_proxies.append(proxy)
            if 'socks5' in protocols:
                socks5_proxies.append(proxy)
            if 'https' in protocols:
                ssl_proxies.append(proxy)
            if 'http' in protocols:
                http_proxies.append(proxy)

        pagination = soup.find('ul', {'class': 'pagination'})
        if not pagination:
            break

        next_page = pagination.find_all('li')[-1].find('a')
        if not next_page or 'href' not in next_page.attrs or '»' not in next_page.text:
            break

        page += 1

    return socks4_proxies, socks5_proxies, ssl_proxies, http_proxies

# Proxy kontrol ve kaydetme fonksiyonları
def check_proxy(proxy, protocol, output_file):
    test_url = 'http://httpbin.org/ip'
    proxies = {
        'http': f'{protocol}://{proxy}',
        'https': f'{protocol}://{proxy}'
    }

    try:
        response = requests.get(test_url, proxies=proxies, timeout=5,allow_redirects=False)
        if response.status_code == 200:
            print(f"{proxy} - {protocol} It's Works")
            save_proxy(proxy, output_file)
            return True
        else:
            print(f"{proxy} - {protocol} FAILED: {response.status_code}")
            return False
    except RequestException:
        print(f"{proxy} - {protocol} Didn't Connect")
        return False

def save_proxy(proxy, file_path):
    with open(file_path, 'a') as file:
        file.write(f"{proxy}\n")

def load_proxies(file_path):
    with open(file_path, 'r') as file:
        return [line.strip() for line in file.readlines()]

def check_proxies_in_threads(proxies, protocol, output_file, max_threads):
    with ThreadPoolExecutor(max_workers=max_threads) as executor:
        executor.map(lambda proxy: check_proxy(proxy, protocol, output_file), proxies)

def combine_and_uniq_proxies_with_labels(output_files, combined_file):
    combined_proxies = set()
    for file in output_files:
        if os.path.exists(file):
            label = os.path.basename(file).split('_')[0]  # Dosya adının başındaki türü etiket olarak alır
            with open(file, 'r') as f:
                for line in f:
                    line = line.strip()
                    if line:  # Boş satırları atla
                        combined_proxies.add(f"{label} {line}\n")
        else:
            print(f"{file} bulunamadı, eklenmedi.")

    with open(combined_file, 'w') as combined:
        combined.writelines(sorted(combined_proxies))
        print(f"[INFO] Kombine edilmiş proxy listesi {combined_file} dosyasına kaydedildi.")

def save_proxies(proxies, file_path):
    with open(file_path, 'w') as file:
        for proxy in proxies:
            file.write(f"{proxy}\n")

def filter_proxies(proxies):
    unique_proxies = list(set(proxies))
    filtered_proxies = [proxy for proxy in unique_proxies if not proxy.startswith("0.0.0.0")]
    return filtered_proxies

def delete_unchecked_proxy_files(file_paths):
    for file_path in file_paths:
        try:
            os.remove(file_path)
            print(f"Silindi: {file_path}")
        except Exception as e:
            print(f"Silme hatası: {file_path} - {e}")

files_to_update = [
    'all_checked_proxies.txt',
    'http_checked_proxies.txt',
    'socks4_checked_proxies.txt',
    'socks5_checked_proxies.txt',
    'ssl_checked_proxies.txt',
]

def delete_old_files():
    for file in files_to_update:
        file_path = os.path.join(REPO_PATH, file)
        if os.path.exists(file_path):
            os.remove(file_path)
            print(f'{file} silindi.')

if __name__ == "__main__":
    max_threads = 300
    delete_old_files()
    # Proxyleri topla ve kaydet
    proxies_sslproxies = fetch_proxies_from_sslproxies()
    save_proxies(proxies_sslproxies, 'ssl_proxies.txt')
    print(f"SSL Proxies (sslproxies.org): {len(proxies_sslproxies)}")

    socks4_proxies_geonode, socks5_proxies_geonode, ssl_proxies_geonode, http_proxies_geonode = fetch_proxies_from_geonode()

    socks4_proxies_proxyscrape, socks5_proxies_proxyscrape, ssl_proxies_proxyscrape, http_proxies_proxyscrape = fetch_proxies_from_proxyscrape()

    socks4_proxies_advanced, socks5_proxies_advanced, ssl_proxies_advanced, http_proxies_advanced = fetch_proxies_from_advanced_name()

    proxies_socksproxy = fetch_proxies_from_socksproxy()
    save_proxies(proxies_socksproxy, 'socks5_proxies.txt')

    all_socks4_proxies = socks4_proxies_geonode + socks4_proxies_proxyscrape + socks4_proxies_advanced
    save_proxies(all_socks4_proxies, 'socks4_proxies.txt')

    all_socks5_proxies = socks5_proxies_geonode + socks5_proxies_proxyscrape + socks5_proxies_advanced + proxies_socksproxy
    save_proxies(all_socks5_proxies, 'socks5_proxies.txt')

    all_http_proxies = http_proxies_geonode + http_proxies_proxyscrape + http_proxies_advanced
    save_proxies(all_http_proxies, 'http_proxies.txt')

    all_ssl_proxies = proxies_sslproxies + ssl_proxies_geonode + ssl_proxies_proxyscrape + ssl_proxies_advanced
    save_proxies(all_ssl_proxies, 'ssl_proxies.txt')

    all_proxies = all_ssl_proxies + all_socks4_proxies + all_socks5_proxies + all_http_proxies
    filtered_proxies = filter_proxies(all_proxies)
    save_proxies(filtered_proxies, 'all_proxies.txt')

    # Proxylerin geçerlilik kontrolü
    socks4_proxies = load_proxies('socks4_proxies.txt')
    check_proxies_in_threads(socks4_proxies, 'socks4', 'socks4_checked_proxies.txt', max_threads)

    socks5_proxies = load_proxies('socks5_proxies.txt')
    check_proxies_in_threads(socks5_proxies, 'socks5', 'socks5_checked_proxies.txt', max_threads)

    http_proxies = load_proxies('http_proxies.txt')
    check_proxies_in_threads(http_proxies, 'http', 'http_checked_proxies.txt', max_threads)

    ssl_proxies = load_proxies('ssl_proxies.txt')
    check_proxies_in_threads(ssl_proxies, 'https', 'ssl_checked_proxies.txt', max_threads)

    checked_files = [
        'socks4_checked_proxies.txt',
        'socks5_checked_proxies.txt',
        'http_checked_proxies.txt',
        'ssl_checked_proxies.txt'
    ]

    combine_and_uniq_proxies_with_labels(checked_files, 'all_combined_labeled_proxies.txt')
    print(f"Toplam Filtrelenmiş Proxy: {len(filtered_proxies)}")

    # Kontrol edilmemiş proxy listelerini sil
    unchecked_files = [
        'socks4_proxies.txt',
        'socks5_proxies.txt',
        'http_proxies.txt',
        'ssl_proxies.txt',
        'all_proxies.txt'
    ]
    delete_unchecked_proxy_files(unchecked_files)

