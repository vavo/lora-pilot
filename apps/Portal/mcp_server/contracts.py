"""The allowlist is the public API; no generic REST, path or shell tool."""
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

SCOPES = frozenset({'workspace:read', 'datasets:inspect', 'models:read', 'runs:read',
                    'operations:read', 'training:submit', 'training:cancel',
                    'comparison:submit', 'artifacts:export', 'artifacts:read'})
READ_SCOPES = frozenset({'workspace:read', 'datasets:inspect', 'models:read', 'runs:read', 'operations:read'})


class Input(BaseModel):
    model_config = ConfigDict(extra='forbid', strict=True, allow_inf_nan=False)


class Automation(Input):
    enabled: bool = False
    max_steps: int = Field(default=100, ge=1, le=600)
    max_seconds: int = Field(default=1800, ge=60, le=3600)
    max_bytes: int = Field(default=8 * 1024 ** 3, ge=1, le=32 * 1024 ** 3)


class Page(Input):
    cursor: str | None = Field(default=None, max_length=500)
    limit: int = Field(default=50, ge=1, le=100)


class Dataset(Input):
    dataset_id: str = Field(pattern=r'^[a-f0-9]{32}$')


class Run(Input):
    run_id: str = Field(pattern=r'^[a-f0-9]{32}$')


class Operation(Input):
    operation_id: str = Field(pattern=r'^[a-f0-9]{32}$')


class Training(Dataset):
    output_name: str = Field(pattern=r'^[A-Za-z0-9][A-Za-z0-9_-]{0,79}$')
    family: Literal['sdxl'] = 'sdxl'
    profile: Literal['quick_test'] = 'quick_test'
    max_steps: int = Field(default=100, ge=1, le=600)
    max_seconds: int = Field(default=1800, ge=60, le=3600)


class Execute(Input):
    plan_id: str = Field(pattern=r'^[a-f0-9]{32}$')
    request_id: str = Field(pattern=r'^[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$')


class Cancel(Run):
    request_id: str = Field(pattern=r'^[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$')


class Comparison(Run):
    checkpoint_id: str = Field(pattern=r'^[a-f0-9]{32}$')
    prompt: str = Field(min_length=1, max_length=2000)
    seed: int = Field(default=31337, ge=0, le=2**32 - 1)
    strength: float = Field(default=1.0, ge=0, le=2)


class Export(Run):
    checkpoint_id: str = Field(pattern=r'^[a-f0-9]{32}$')
    comparison_id: str | None = Field(default=None, pattern=r'^[a-f0-9]{32}$')
    images: list[int] = Field(default_factory=list, max_length=2)
    sample_prompt: str = Field(default='', max_length=2000)


TOOLS = {
    'workspace_status': (Input, {'workspace:read'}, 'Inspect coarse workspace status. Does not start services.'),
    'datasets_list': (Page, {'datasets:inspect'}, 'List explicitly granted dataset handles. No image or caption bytes.'),
    'dataset_review': (Dataset, {'datasets:inspect'}, 'Inspect a granted dataset. Returns bounded quality counts, never captions.'),
    'models_list': (Page, {'models:read'}, 'List the bundled model catalog and installed state without downloading or seeding files.'),
    'runs_list': (Page, {'runs:read'}, 'List granted training runs without starting the queue.'),
    'run_get': (Run, {'runs:read'}, 'Read structured run status and checkpoint handles. Excludes logs and raw configuration.'),
    'training_plan': (Training, {'datasets:inspect', 'models:read', 'workspace:read'}, 'Prepare an SDXL quick test for owner approval. Does not submit training.'),
    'training_start': (Execute, {'training:submit'}, 'Submit an owner-approved training plan. Retry with the same request_id.'),
    'run_cancel': (Cancel, {'training:cancel'}, 'Cancel a granted managed run. Progress since the last checkpoint can be lost; files are preserved.'),
    'comparison_plan': (Comparison, {'runs:read', 'models:read'}, 'Plan a fixed baseline and LoRA comparison for owner approval. Publishes nothing.'),
    'comparison_start': (Execute, {'comparison:submit'}, 'Execute an approved comparison once. Unknown outcomes require owner reconciliation.'),
    'export_plan': (Export, {'runs:read'}, 'Review checkpoint export disclosure. Original dataset and logs are excluded; model weights can retain training information.'),
    'export_create': (Execute, {'artifacts:export'}, 'Create the approved private archive once. Retry using the same request_id.'),
    'operation_get': (Operation, {'operations:read'}, 'Observe an owned operation. Polling never resubmits it.'),
}
MUTATIONS = frozenset({'training_start', 'run_cancel', 'comparison_start', 'export_create'})
