# Nmap Cheat Sheet 2025: All Commands & Flags

## Target Specification
(Xác định mục tiêu)

* **Quét một IP duy nhất:**
    ```
    nmap 192.168.1.1
    ```
* **Quét nhiều IP cụ thể:**
    ```
    nmap 192.168.1.1 192.168.2.1
    ```
* **Quét một dải IP:**
    ```
    nmap 192.168.1.1-254
    ```
* **Quét một tên miền:**
    ```
    nmap scanme.nmap.org
    ```
* **Quét một mạng con (CIDR):**
    ```
    nmap 192.168.1.0/24
    ```
* **`-iL <file>`**: Quét các mục tiêu từ một file.
    ```
    nmap -iL targets.txt
    ```
* **`-iR <số lượng>`**: Quét một số lượng host ngẫu nhiên.
    ```
    nmap -iR 100
    ```
* **`--exclude <host>`**: Loại trừ các host khỏi quá trình quét.
    ```
    nmap 192.168.1.0/24 --exclude 192.168.1.1
    ```

---

## Nmap Scan Techniques
(Các kỹ thuật quét)

* **`-sS`**: TCP SYN port scan (quét SYN, hay quét nửa kết nối). Đây là kiểu quét mặc định khi có quyền root, rất nhanh và kín đáo.
    ```
    nmap 192.168.1.1 -sS
    ```
* **`-sT`**: TCP connect port scan (quét kết nối đầy đủ). Mặc định khi không có quyền root. Chậm hơn và dễ bị phát hiện hơn -sS.
    ```
    nmap 192.168.1.1 -sT
    ```
* **`-sU`**: UDP port scan (quét cổng UDP).
    ```
    nmap 192.168.1.1 -sU
    ```
* **`-sA`**: TCP ACK port scan. Thường dùng để kiểm tra rule của firewall.
    ```
    nmap 192.168.1.1 -sA
    ```

---

## Host Discovery
(Phát hiện Host)

* **`-sL`**: List Scan. Chỉ liệt kê các mục tiêu mà không gửi bất kỳ gói tin nào.
    ```
    nmap 192.168.1.1-3 -sL
    ```
* **`-sn`**: Ping Scan. Chỉ phát hiện host nào đang online mà không quét cổng.
    ```
    nmap 192.168.1.1/24 -sn
    ```
* **`-Pn`**: No Ping. Bỏ qua bước phát hiện host và coi như tất cả các host đều online. Hữu ích khi mục tiêu chặn gói tin ping.
    ```
    nmap 192.168.1.1 -Pn
    ```
* **`-PS <portlist>`**: Gửi gói tin TCP SYN đến các cổng chỉ định để phát hiện host.
    ```
    nmap 192.168.1.1-5 -PS22-25,80
    ```
* **`-PR`**: ARP discovery. Quét ARP trên mạng nội bộ, rất nhanh và đáng tin cậy.
    ```
    nmap 192.168.1.1/24 -PR
    ```

---

## Port Specification
(Chỉ định cổng)

* **`-p <port>`**: Quét một cổng cụ thể.
    ```
    nmap 192.168.1.1 -p 21
    ```
* **`-p <range>`**: Quét một dải cổng.
    ```
    nmap 192.168.1.1 -p 21-100
    ```
* **`-p U:<port>,T:<port>`**: Quét các cổng UDP và TCP cụ thể.
    ```
    nmap 192.168.1.1 -p U:53,T:21-25,80
    ```
* **`-p-`**: Quét tất cả 65535 cổng.
    ```
    nmap 192.168.1.1 -p-
    ```
* **`-F`**: Fast scan. Chỉ quét 100 cổng phổ biến nhất.
    ```
    nmap 192.168.1.1 -F
    ```
* **`--top-ports <số lượng>`**: Quét top N cổng phổ biến nhất.
    ```
    nmap 192.168.1.1 --top-ports 20
    ```

---

## Service and Version Detection
(Phát hiện Dịch vụ và Phiên bản)

* **`-sV`**: Cố gắng xác định phiên bản của dịch vụ đang chạy trên các cổng mở.
    ```
    nmap 192.168.1.1 -sV
    ```
* **`--version-intensity <mức độ>`**: Thiết lập mức độ dò phiên bản từ 0 (nhẹ) đến 9 (toàn diện).
    ```
    nmap 192.168.1.1 -sV --version-intensity 8
    ```
* **`-A`**: Aggressive scan. Bật chế độ quét tấn công, bao gồm phát hiện OS, phát hiện phiên bản, quét script, và traceroute.
    ```
    nmap 192.168.1.1 -A
    ```

---

## OS Detection
(Phát hiện Hệ điều hành)

* **`-O`**: Bật tính năng phát hiện hệ điều hành từ xa.
    ```
    nmap 192.168.1.1 -O
    ```
* **`--osscan-guess`**: Bắt Nmap phải "đoán" hệ điều hành một cách quyết liệt hơn.
    ```
    nmap 192.168.1.1 -O --osscan-guess
    ```

---

## Timing and Performance
(Thời gian và Hiệu suất)

* **`-T<0-5>`**: Thiết lập mẫu thời gian quét. `T0` (paranoid) là chậm nhất để né IDS, `T5` (insane) là nhanh nhất. `T4` (aggressive) thường được dùng trong các cuộc thi CTF.
    ```
    nmap 192.168.1.1 -T4
    ```

---

## NSE Scripts
(Sử dụng Nmap Scripting Engine)

* **`-sC`** hoặc **`--script=default`**: Chạy bộ script mặc định, an toàn và hữu ích cho việc khám phá.
    ```
    nmap 192.168.1.1 -sC
    ```
* **`--script=<tên script>`**: Chạy một script cụ thể.
    ```
    nmap 192.168.1.1 --script=http-title
    ```
* **`--script=<mẫu>`**: Chạy các script khớp với một mẫu.
    ```
    nmap 192.168.1.1 --script="http-vuln-*"
    ```
* **`--script-args`**: Cung cấp tham số cho script.
    ```
    nmap --script=dns-brute --script-args dns-brute.domain=example.com
    ```
* **Ví dụ hữu ích:**
    * Phát hiện lỗ hổng SQL Injection: `nmap -p80 --script http-sql-injection scanme.nmap.org`
    * Phát hiện lỗ hổng XSS: `nmap -p80 --script http-unsafe-output-escaping scanme.nmap.org`

---

## Firewall / IDS Evasion and Spoofing
(Né tránh Firewall / IDS và Giả mạo)

* **`-f`**: Phân mảnh gói tin, làm cho việc phát hiện của các bộ lọc gói tin trở nên khó khăn hơn.
    ```
    nmap 192.168.1.1 -f
    ```
* **`-D <decoy1,decoy2...>`**: Giả mạo IP nguồn (decoy). Khiến cho mục tiêu nghĩ rằng nó đang bị quét bởi nhiều IP khác nhau, che giấu IP thật của em.
    ```
    nmap -D RND:10 192.168.1.1
    ```
* **`-S <IP>`**: Giả mạo địa chỉ IP nguồn.
    ```
    nmap -S 10.10.10.11 192.168.1.1
    ```
* **`-g <port>`** hoặc **`--source-port <port>`**: Sử dụng một cổng nguồn cụ thể.
    ```
    nmap -g 53 192.168.1.1
    ```
* **`--data-length <số>`**: Thêm dữ liệu ngẫu nhiên vào cuối các gói tin.
    ```
    nmap --data-length 25 192.168.1.1
    ```

---

## Output
(Lưu kết quả)

* **`-oN <file>`**: Lưu kết quả ra file text thông thường.
    ```
    nmap 192.168.1.1 -oN result.txt
    ```
* **`-oX <file>`**: Lưu kết quả ra file XML.
    ```
    nmap 192.168.1.1 -oX result.xml
    ```
* **`-oG <file>`**: Lưu kết quả ra file định dạng Grepable.
    ```
    nmap 192.168.1.1 -oG result.txt
    ```
* **`-oA <basename>`**: Lưu kết quả ra cả 3 định dạng cùng lúc.
    ```
    nmap 192.168.1.1 -oA results
    ```
* **`-v`**: Tăng mức độ chi tiết của output. Sử dụng `-vv` hoặc `-vvv` để chi tiết hơn nữa.
    ```
    nmap 192.168.1.1 -vv
    ```

---

## Miscellaneous
(Khác)

* **`-6`**: Bật chế độ quét IPv6.
    ```
    nmap -6 ::1
    ```
* **`-h`**: Hiển thị màn hình trợ giúp.
    ```
    nmap -h
    ```
