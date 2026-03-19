---
name: db-query
description: Run a SQL query against Supabase
disable-model-invocation: true
---

# Database Query

Run a SQL query against Supabase PostgreSQL.

**Usage:**
```
/db-query <sql_query>
```

**Example:**
```
/db-query SELECT * FROM posts WHERE status = 'ready' LIMIT 10
```

**Methods:**

**Option 1 - Via Supabase CLI (requires supabase CLI):**
```bash
supabase db execute -q "<sql_query>"
```

**Option 2 - Via Supabase REST API:**
```bash
curl -X POST 'https://<project-ref>.supabase.co/rest/v1/rpc/exec_sql' \
  -H "apikey: $SUPABASE_SERVICE_KEY" \
  -H "Authorization: Bearer $SUPABASE_SERVICE_KEY" \
  -H "Content-Type: application/json" \
  -d '{"query": "<sql_query>"}'
```

**Option 3 - Via psql:**
```bash
psql "$SUPABASE_DB_URL" -c "<sql_query>"
```

**Notes:**
- Use SUPABASE_SERVICE_KEY for admin access
- Never run destructive queries (DROP, DELETE without WHERE) without confirmation
- pgvector tables: posts (embedding column), use `<->` for similarity search
