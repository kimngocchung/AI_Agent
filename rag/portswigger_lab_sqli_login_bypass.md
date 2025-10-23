# Writeup: PortSwigger Lab - SQL injection vulnerability allowing login bypass

## Lab Information
- **Tên Lab:** SQL injection vulnerability in the login function.
- **Mục tiêu:** Thực hiện một cuộc tấn công SQL injection để đăng nhập vào ứng dụng với tư cách người dùng `administrator`.

---

## Phân tích
Lỗ hổng nằm ở chức năng đăng nhập của ứng dụng. Bằng cách thao túng câu lệnh SQL, chúng ta có thể bỏ qua hoàn toàn việc kiểm tra mật khẩu.

Kỹ thuật cốt lõi là sử dụng một chuỗi **comment (chú thích)** trong SQL để làm cho phần còn lại của câu lệnh (phần kiểm tra mật khẩu) bị vô hiệu hóa. Trong hầu hết các cơ sở dữ liệu SQL, hai dấu gạch ngang (`--`) có nghĩa là "bỏ qua mọi thứ từ đây cho đến hết dòng".

---

## Khai thác (Exploitation)
Để giải quyết lab, chúng ta cần xây dựng một payload khiến cho câu truy vấn chỉ kiểm tra tên người dùng mà không kiểm tra mật khẩu.

1.  Truy cập vào trang đăng nhập của lab.

2.  Trong trường **Username**, nhập vào payload sau:
    ```sql
    administrator'--
    ```

3.  Để trống trường **Password**.

4.  Nhấn nút đăng nhập.

### Giải thích chi tiết
- **Câu truy vấn SQL gốc** của server có thể trông như thế này:
    ```sql
    SELECT * FROM users WHERE username = '[USERNAME_INPUT]' AND password = '[PASSWORD_INPUT]'
    ```

- Khi chúng ta nhập payload `administrator'--`, câu truy vấn trên server sẽ trở thành:
    ```sql
    SELECT * FROM users WHERE username = 'administrator'--' AND password = ''
    ```

- Vì `--` là một chuỗi comment, cơ sở dữ liệu sẽ thực thi câu lệnh như sau:
    ```sql
    SELECT * FROM users WHERE username = 'administrator'
    ```
- Câu lệnh này hoàn toàn hợp lệ. Nó sẽ trả về bản ghi của người dùng `administrator`, và ứng dụng sẽ đăng nhập thành công mà không cần mật khẩu.
