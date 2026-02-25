"""Initial schema with domains, metadata, and features tables.

Revision ID: 001
Revises: 
Create Date: 2026-02-20

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = '001'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'domains',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('domain', sa.String(length=253), nullable=False),
        sa.Column('entropy', sa.Float(), nullable=True),
        sa.Column('risk_score', sa.String(length=20), nullable=False, server_default='Unknown'),
        sa.Column('category', sa.String(length=50), nullable=False, server_default='Unknown'),
        sa.Column('summary', sa.String(length=2000), nullable=True),
        sa.Column('is_anomaly', sa.Boolean(), nullable=False, server_default='0'),
        sa.Column('anomaly_score', sa.Float(), nullable=False, server_default='0.0'),
        sa.Column('analysis_source', sa.String(length=30), nullable=False, server_default='unknown'),
        sa.Column('timestamp', sa.DateTime(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('domain'),
    )
    op.create_index('idx_domains_domain', 'domains', ['domain'])
    op.create_index('idx_domains_created_at', 'domains', ['created_at'])
    op.create_index('idx_domains_category', 'domains', ['category'])
    op.create_index('idx_domains_risk_score', 'domains', ['risk_score'])
    op.create_index('idx_domains_is_anomaly', 'domains', ['is_anomaly'])

    op.create_table(
        'metadata',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('domain_id', sa.Integer(), nullable=False),
        sa.Column('reason', sa.String(length=100), nullable=True),
        sa.Column('filter_id', sa.Integer(), nullable=True),
        sa.Column('rule', sa.String(length=500), nullable=True),
        sa.Column('client', sa.String(length=100), nullable=True),
        sa.ForeignKeyConstraint(['domain_id'], ['domains.id'], ),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('idx_metadata_domain_id', 'metadata', ['domain_id'])

    op.create_table(
        'features',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('domain_id', sa.Integer(), nullable=False),
        sa.Column('length', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('digit_ratio', sa.Float(), nullable=False, server_default='0.0'),
        sa.Column('vowel_ratio', sa.Float(), nullable=False, server_default='0.0'),
        sa.Column('non_alphanumeric', sa.Integer(), nullable=False, server_default='0'),
        sa.ForeignKeyConstraint(['domain_id'], ['domains.id'], ),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('idx_features_domain_id', 'features', ['domain_id'])


def downgrade() -> None:
    op.drop_index('idx_features_domain_id', table_name='features')
    op.drop_table('features')
    
    op.drop_index('idx_metadata_domain_id', table_name='metadata')
    op.drop_table('metadata')
    
    op.drop_index('idx_domains_is_anomaly', table_name='domains')
    op.drop_index('idx_domains_risk_score', table_name='domains')
    op.drop_index('idx_domains_category', table_name='domains')
    op.drop_index('idx_domains_created_at', table_name='domains')
    op.drop_index('idx_domains_domain', table_name='domains')
    op.drop_table('domains')
