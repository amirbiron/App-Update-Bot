# MongoDB Atlas Connection Troubleshooting Guide
# מדריך פתרון בעיות חיבור MongoDB Atlas

## Common SSL/TLS Issues and Solutions
## בעיות SSL/TLS נפוצות ופתרונות

### 1. SSL Handshake Failed Error
### שגיאת SSL Handshake Failed

**Error Message:**
```
SSL handshake failed: [SSL: TLSV1_ALERT_INTERNAL_ERROR] tlsv1 alert internal error
```

**Solutions:**
1. **Use the updated connection settings** (already implemented in the code):
   ```python
   client = MongoClient(
       mongo_uri,
       ssl=True,
       ssl_cert_reqs='CERT_NONE',
       tlsAllowInvalidCertificates=True,
       tlsAllowInvalidHostnames=True
   )
   ```

2. **Check your MongoDB Atlas connection string**:
   - Make sure it starts with `mongodb+srv://` or `mongodb://`
   - Verify username and password are correct
   - Ensure the cluster name is correct

3. **Network/Firewall issues**:
   - Check if your IP is whitelisted in MongoDB Atlas
   - Try connecting from a different network
   - Disable VPN if using one

### 2. Connection String Format
### פורמט מחרוזת החיבור

**Correct format for MongoDB Atlas:**
```
mongodb+srv://username:password@cluster-name.xxxxx.mongodb.net/database?retryWrites=true&w=majority
```

**Important parameters:**
- `retryWrites=true` - Enables automatic retry for write operations
- `w=majority` - Ensures write acknowledgment from majority of replica set

### 3. Environment Variable Setup
### הגדרת משתנה סביבה

**Linux/Mac:**
```bash
export MONGO_URI='your_mongodb_connection_string'
```

**Windows:**
```cmd
set MONGO_URI=your_mongodb_connection_string
```

**PowerShell:**
```powershell
$env:MONGO_URI='your_mongodb_connection_string'
```

### 4. Testing Connection
### בדיקת החיבור

Run the test script:
```bash
python test_mongodb.py
```

Or use the main test script:
```bash
python test.py
```

### 5. Alternative Solutions
### פתרונות חלופיים

If SSL issues persist:

1. **Try without explicit SSL settings**:
   ```python
   client = MongoClient(mongo_uri)
   ```

2. **Update pymongo version**:
   ```bash
   pip install --upgrade pymongo[srv]
   ```

3. **Check Python SSL library**:
   ```bash
   python -c "import ssl; print(ssl.OPENSSL_VERSION)"
   ```

### 6. MongoDB Atlas Dashboard Checks
### בדיקות בלוח הבקרה של MongoDB Atlas

1. **Network Access**:
   - Go to Network Access in Atlas
   - Add your IP address or use `0.0.0.0/0` for all IPs (not recommended for production)

2. **Database Access**:
   - Verify your database user exists
   - Check user permissions

3. **Cluster Status**:
   - Ensure cluster is running
   - Check for any maintenance windows

### 7. Common Mistakes
### טעויות נפוצות

1. **Wrong connection string format**
2. **Incorrect username/password**
3. **IP not whitelisted**
4. **Using old pymongo version**
5. **Missing required parameters in connection string**

### 8. Debug Information
### מידע לדיבוג

To get more detailed error information, you can enable debug logging:

```python
import logging
logging.basicConfig(level=logging.DEBUG)
```

### 9. Contact Support
### יצירת קשר עם התמיכה

If all else fails:
1. Check MongoDB Atlas status page
2. Contact MongoDB support
3. Check community forums

---

## Quick Fix Checklist
## רשימת בדיקה לפתרון מהיר

- [ ] Connection string format is correct
- [ ] Username and password are correct
- [ ] IP address is whitelisted in Atlas
- [ ] Using latest pymongo version
- [ ] Environment variable is set correctly
- [ ] Network connectivity is working
- [ ] MongoDB Atlas cluster is running

---

*Last updated: 2024*