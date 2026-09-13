import pytest

from app.widget.dependencies import get_widget_tenant


@pytest.mark.anyio
async def test_widget_tenant_can_be_resolved_from_database(
    db_session,
    existing_tenant,
):
    resolved = await get_widget_tenant(
        site_key=existing_tenant.site_key,
        origin=None,
        session=db_session,
    )

    assert resolved.id == existing_tenant.id
    assert resolved.site_key == existing_tenant.site_key