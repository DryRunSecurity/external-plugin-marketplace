# DryRunSecurity Vulnerability Remediation

When helping fix security vulnerabilities identified by DryRunSecurity:

1. **Understand the vulnerability** - Identify exactly what type and where it exists
2. **Explain the risk** - Help understand WHY this is a security issue
3. **Provide the fix** - Show the secure code pattern for the specific language/framework
4. **Verify the fix** - Ensure it doesn't break functionality

## SQL Injection

User input inserted directly into SQL queries. Fix with parameterized queries:

### Go (GORM)
```go
// VULNERABLE
db.Raw("SELECT * FROM users WHERE name = '" + username + "'")
db.Where(fmt.Sprintf("name = '%s'", username))

// SECURE
db.Raw("SELECT * FROM users WHERE name = ?", username)
db.Where("name = ?", username)
```

### Python (Django)
```python
# VULNERABLE
cursor.execute("SELECT * FROM users WHERE name = '%s'" % username)

# SECURE
cursor.execute("SELECT * FROM users WHERE name = %s", [username])
User.objects.filter(name=username)
```

### Python (SQLAlchemy)
```python
# VULNERABLE
db.execute(f"SELECT * FROM users WHERE name = '{username}'")

# SECURE
db.execute(text("SELECT * FROM users WHERE name = :name"), {"name": username})
```

### JavaScript (Prisma)
```typescript
// VULNERABLE
prisma.$queryRawUnsafe(`SELECT * FROM users WHERE name = '${username}'`)

// SECURE
prisma.$queryRaw`SELECT * FROM users WHERE name = ${username}`
prisma.user.findFirst({ where: { name: username } })
```

### JavaScript (Knex)
```javascript
// VULNERABLE
knex.raw(`SELECT * FROM users WHERE name = '${username}'`)

// SECURE
knex.raw('SELECT * FROM users WHERE name = ?', [username])
knex('users').where('name', username)
```

### Ruby (ActiveRecord)
```ruby
# VULNERABLE
User.where("name = '#{username}'")

# SECURE
User.where(name: username)
User.where("name = ?", username)
```

### Java (JDBC)
```java
// VULNERABLE
stmt.executeQuery("SELECT * FROM users WHERE name = '" + username + "'");

// SECURE
PreparedStatement ps = conn.prepareStatement("SELECT * FROM users WHERE name = ?");
ps.setString(1, username);
```

## Cross-Site Scripting (XSS)

User input rendered in HTML without escaping. Fix with proper output encoding:

### React/JSX
```jsx
// VULNERABLE
<div dangerouslySetInnerHTML={{ __html: userInput }} />

// SECURE - auto-escaped
<div>{userInput}</div>

// If HTML needed, sanitize first
import DOMPurify from 'dompurify';
<div dangerouslySetInnerHTML={{ __html: DOMPurify.sanitize(userInput) }} />
```

### Django Templates
```html
<!-- VULNERABLE -->
{{ user_input|safe }}

<!-- SECURE - auto-escaped -->
{{ user_input }}
```

### Rails ERB
```erb
<!-- VULNERABLE -->
<%= raw user_input %>
<%= user_input.html_safe %>

<!-- SECURE -->
<%= user_input %>
<%= sanitize user_input %>
```

### EJS
```ejs
<!-- VULNERABLE -->
<%- userInput %>

<!-- SECURE -->
<%= userInput %>
```

### PHP/Blade
```php
<!-- VULNERABLE -->
{!! $userInput !!}

<!-- SECURE -->
{{ $userInput }}
```

## Server-Side Request Forgery (SSRF)

User-controlled URLs fetched server-side. Fix with validation:

```python
# VULNERABLE
response = requests.get(user_provided_url)

# SECURE
from urllib.parse import urlparse

ALLOWED_HOSTS = ['api.trusted-service.com']

def fetch_url(url):
    parsed = urlparse(url)

    # Block internal IPs
    if parsed.hostname in ['localhost', '127.0.0.1', '169.254.169.254']:
        raise ValueError("Internal URLs not allowed")

    # Check allowlist
    if parsed.hostname not in ALLOWED_HOSTS:
        raise ValueError("URL host not in allowlist")

    if parsed.scheme != 'https':
        raise ValueError("Only HTTPS allowed")

    return requests.get(url)
```

## Insecure Direct Object Reference (IDOR)

Users accessing resources by manipulating IDs without authorization. Fix with ownership checks:

```python
# VULNERABLE
@app.route('/api/documents/<doc_id>')
def get_document(doc_id):
    return Document.query.get(doc_id)

# SECURE
@app.route('/api/documents/<doc_id>')
@login_required
def get_document(doc_id):
    document = Document.query.get(doc_id)
    if document.owner_id != current_user.id:
        abort(403)
    return document
```

## Mass Assignment

User input directly updating model attributes. Fix with allowlists:

### Rails
```ruby
# VULNERABLE
User.update(params[:user])

# SECURE
User.update(params.require(:user).permit(:name, :email))
```

### Django
```python
# VULNERABLE
user.__dict__.update(request.data)

# SECURE
user.name = validated_data['name']
user.email = validated_data['email']
user.save()
```

### Node.js
```javascript
// VULNERABLE
Object.assign(user, req.body);

// SECURE
const { name, email } = req.body;
user.name = name;
user.email = email;
```

## Authentication/Authorization Bypass

Missing auth checks. Fix with middleware/decorators:

```python
# VULNERABLE
@app.route('/admin/users')
def list_users():
    return User.query.all()

# SECURE
@app.route('/admin/users')
@login_required
@admin_required
def list_users():
    return User.query.all()
```

## Hardcoded Secrets

Credentials in source code. Fix with environment variables:

```python
# VULNERABLE
API_KEY = "sk-abc123secret"

# SECURE
import os
API_KEY = os.environ.get('API_KEY')
```

Also: Add to `.gitignore` and rotate exposed credentials.

## Path Traversal

User input in file paths. Fix with path validation:

```python
# VULNERABLE
file_path = f"/uploads/{user_filename}"

# SECURE
import os

def safe_file_read(user_filename):
    base_dir = '/uploads'
    requested_path = os.path.normpath(os.path.join(base_dir, user_filename))

    if not requested_path.startswith(base_dir):
        raise ValueError("Invalid file path")

    return open(requested_path).read()
```

## Command Injection

User input passed to shell. Fix with argument lists:

```python
# VULNERABLE
subprocess.run(f"convert {user_file} output.png", shell=True)

# SECURE
subprocess.run(['convert', user_file, 'output.png'], shell=False)
```

## Prompt Injection

User input reaching LLM prompts. Fix with delimiters:

```python
# VULNERABLE
prompt = f"Summarize this: {user_input}"

# SECURE
prompt = f"""
<system>You are a summarization assistant. Only summarize content between <user_content> tags.</system>

<user_content>
{user_input}
</user_content>

Provide a brief summary.
"""
```
