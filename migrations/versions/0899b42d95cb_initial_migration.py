"""Initial Migration

Revision ID: 0899b42d95cb
Revises: 
Create Date: 2024-02-04 01:32:49.430881

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '0899b42d95cb'
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    # Remove any database tables or constraints you don't want to drop
    # Comment out or remove the lines below that you want to keep
    
    # op.drop_index('procrastinate_events_job_id_fkey', table_name='procrastinate_events')
    # op.drop_table('procrastinate_events')
    # op.drop_index('procrastinate_jobs_id_lock_idx', table_name='procrastinate_jobs')
    # op.drop_index('procrastinate_jobs_lock_idx', table_name='procrastinate_jobs')
    # op.drop_index('procrastinate_jobs_queue_name_idx', table_name='procrastinate_jobs')
    # op.drop_index('procrastinate_jobs_queueing_lock_idx', table_name='procrastinate_jobs')
    # op.drop_table('procrastinate_jobs')
    # op.drop_index('procrastinate_periodic_defers_job_id_fkey', table_name='procrastinate_periodic_defers')
    # op.drop_table('procrastinate_periodic_defers')
    
    # Add any columns, tables, indexes, or constraints you need for the upgrade
    op.add_column('users', sa.Column('oidc_identifier', sa.String(length=255), nullable=True))
    op.create_unique_constraint(None, 'users', ['oidc_identifier'])
    
    # ### end Alembic commands ###


def downgrade():
    # Adjust the downgrade script as needed to reverse the changes made in upgrade()
    # Comment out or remove the lines below that you want to keep
    
    # op.drop_constraint(None, 'users', type_='unique')
    op.drop_column('users', 'oidc_identifier')
    
    # Re-add the tables, indexes, constraints, etc. that were removed in upgrade()
    # Example:
    # op.create_table('procrastinate_periodic_defers',
    # ...
    # )
    # op.create_index('procrastinate_periodic_defers_job_id_fkey', 'procrastinate_periodic_defers', ['job_id'], unique=False)
    
    # ### end Alembic commands ###