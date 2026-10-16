from sqlalchemy import create_engine, inspect

url = "postgresql+psycopg2://postgres.vgquhttvlrvvwpilawho:y8U3%27w%5EPhR%2CpnVZ@aws-0-ap-southeast-1.pooler.supabase.com:6543/postgres?sslmode=require"

engine = create_engine(url, connect_args={"sslmode": "require", "connect_timeout": 5})
with engine.connect() as conn:
    insp = inspect(engine)
    tables = insp.get_table_names(schema="public")
    print("SQLALCHEMY CONNECTED SUCCESSFULLY!")
    print("Discovered public tables count:", len(tables))
    for t in tables:
        cols = insp.get_columns(t, schema="public")
        print(f"  - {t}: {[c['name'] for c in cols]}")

engine.dispose()
