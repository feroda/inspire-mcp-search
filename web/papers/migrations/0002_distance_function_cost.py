from django.db import migrations

# pgvector ships cosine_distance with the default procost of 1 — the same cost
# Postgres assigns to comparing two integers. A 768-dimensional distance is
# ~768 multiply-adds, so the planner badly underestimates a sequential scan and
# rejects the HNSW index, whose startup cost it estimates conservatively.
#
# Measured on ~2000 rows: seq scan 12.2ms (estimated 739.98) versus HNSW index
# scan 1.4ms (estimated startup 891.32). Declaring a truthful cost makes the
# planner choose the index without enable_seqscan hacks.
COST = 100


class Migration(migrations.Migration):

    dependencies = [
        ('papers', '0001_initial'),
    ]

    operations = [
        migrations.RunSQL(
            sql=f"ALTER FUNCTION cosine_distance(vector, vector) COST {COST};",
            reverse_sql="ALTER FUNCTION cosine_distance(vector, vector) COST 1;",
        ),
    ]
