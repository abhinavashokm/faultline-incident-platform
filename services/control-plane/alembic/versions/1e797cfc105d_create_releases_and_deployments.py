"""Create the Control Plane release and deployment tables.

Revision ID: 1e797cfc105d
Revises: 0004
"""

from alembic import op


revision: str = "1e797cfc105d"
down_revision: str = "0004"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("""
        CREATE TABLE control.releases (
            id uuid NOT NULL,
            workspace_id uuid NOT NULL,
            project_id uuid NOT NULL,
            version character varying(150) NOT NULL,
            commit_sha character varying(64),
            artifact_ref character varying(300),
            created_by_key_id uuid NOT NULL,
            created_at timestamp with time zone DEFAULT now() NOT NULL,
            CONSTRAINT releases_commit_sha_ck CHECK (((commit_sha)::text ~ '^[0-9a-f]+$'::text)),
            CONSTRAINT releases_version_ck CHECK ((((version)::text <> ''::text) AND ((version)::text !~ '[[:space:]]'::text))),
            CONSTRAINT releases_pkey PRIMARY KEY (id),
            CONSTRAINT releases_project_version_uq UNIQUE (project_id, version),
            CONSTRAINT releases_workspace_project_id_uq UNIQUE (workspace_id, project_id, id),
            CONSTRAINT releases_created_by_key_fk FOREIGN KEY (created_by_key_id) REFERENCES control.project_api_keys(id),
            CONSTRAINT releases_project_fk FOREIGN KEY (workspace_id, project_id) REFERENCES control.projects(workspace_id, id)
        )
    """)
    op.execute(
        "CREATE INDEX releases_project_commit_sha_idx "
        "ON control.releases USING btree (project_id, commit_sha)"
    )
    op.execute(
        "CREATE INDEX releases_project_created_at_idx "
        "ON control.releases USING btree (project_id, created_at)"
    )
    op.execute("""
        CREATE TABLE control.deployments (
            id uuid NOT NULL,
            workspace_id uuid NOT NULL,
            project_id uuid NOT NULL,
            release_id uuid NOT NULL,
            environment character varying(100) NOT NULL,
            kind character varying(20) DEFAULT 'deploy'::character varying NOT NULL,
            status character varying(30) DEFAULT 'pending'::character varying NOT NULL,
            rollback_of_deployment_id uuid,
            external_run_id character varying(100),
            deployed_by uuid,
            deployed_by_key_id uuid,
            failure_reason character varying(500),
            metadata jsonb,
            created_at timestamp with time zone DEFAULT now() NOT NULL,
            started_at timestamp with time zone,
            finished_at timestamp with time zone,
            CONSTRAINT deployments_actor_ck CHECK (((deployed_by IS NULL) <> (deployed_by_key_id IS NULL))),
            CONSTRAINT deployments_environment_ck CHECK (((environment)::text ~ '^[a-z0-9_-]+$'::text)),
            CONSTRAINT deployments_finished_at_ck CHECK ((finished_at >= started_at)),
            CONSTRAINT deployments_kind_ck CHECK (((kind)::text = ANY ((ARRAY['deploy'::character varying, 'rollback'::character varying])::text[]))),
            CONSTRAINT deployments_status_ck CHECK (((status)::text = ANY ((ARRAY['pending'::character varying, 'running'::character varying, 'success'::character varying, 'failed'::character varying, 'cancelled'::character varying, 'rolled_back'::character varying])::text[]))),
            CONSTRAINT deployments_pkey PRIMARY KEY (id),
            CONSTRAINT deployments_project_external_run_uq UNIQUE (project_id, external_run_id),
            CONSTRAINT deployments_deployed_by_fk FOREIGN KEY (deployed_by) REFERENCES control.users(id),
            CONSTRAINT deployments_deployed_by_key_fk FOREIGN KEY (deployed_by_key_id) REFERENCES control.project_api_keys(id),
            CONSTRAINT deployments_project_fk FOREIGN KEY (workspace_id, project_id) REFERENCES control.projects(workspace_id, id),
            CONSTRAINT deployments_release_fk FOREIGN KEY (workspace_id, project_id, release_id) REFERENCES control.releases(workspace_id, project_id, id),
            CONSTRAINT deployments_rollback_of_fk FOREIGN KEY (rollback_of_deployment_id) REFERENCES control.deployments(id)
        )
    """)
    op.execute(
        "CREATE UNIQUE INDEX deployments_project_environment_active_uq "
        "ON control.deployments USING btree (project_id, environment) WHERE ((status)::text = ANY ((ARRAY['pending'::character varying, 'running'::character varying])::text[]))"
    )
    op.execute(
        "CREATE INDEX deployments_project_environment_created_at_idx "
        "ON control.deployments USING btree (project_id, environment, created_at)"
    )


def downgrade() -> None:
    op.drop_table("deployments", schema="control")
    op.drop_table("releases", schema="control")
