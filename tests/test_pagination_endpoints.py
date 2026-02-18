from __future__ import annotations

from app.models.customer_forwarder import CustomerForwarder
from app.models.customer_master import CustomerMaster
from app.models.customer_role import CustomerRole
from app.models.forwarder_port import ForwarderPortMap
from app.models.logistics_lookups import PortLookup
from app.models.partner_master import PartnerMaster
from app.models.partner_role import PartnerRole
from app.models.user_customer_link import UserCustomerLink
from app.models.user_partner_link import UserPartnerLink
from app.models.users import User


def _seed_roles(db_session):
    db_session.add_all(
        [
            PartnerRole(id=1, role_code="FORWARDER", role_name="Forwarder", is_active=True),
            CustomerRole(id=1, role_code="B2B", role_name="B2B", is_active=True),
        ]
    )
    db_session.commit()


def _seed_user(db_session, idx: int) -> User:
    user = User(
        id=idx,
        username=f"user{idx}",
        email=f"user{idx}@example.com",
        is_active=True,
        clearance=0,
    )
    db_session.add(user)
    db_session.commit()
    return user


def _seed_partner(db_session, idx: int) -> PartnerMaster:
    partner = PartnerMaster(
        id=idx,
        partner_identifier=f"VEN-{idx:04d}",
        role_id=1,
        legal_name=f"Partner {idx}",
        preferred_currency="USD",
        is_active=True,
        is_verified=True,
    )
    db_session.add(partner)
    db_session.commit()
    return partner


def _seed_customer(db_session, idx: int) -> CustomerMaster:
    customer = CustomerMaster(
        id=idx,
        customer_identifier=f"CUST-{idx:04d}",
        role_id=1,
        legal_name=f"Customer {idx}",
        preferred_currency="USD",
        is_active=True,
        is_verified=True,
        created_by="seed@local",
        last_changed_by="seed@local",
    )
    db_session.add(customer)
    db_session.commit()
    return customer


def _seed_port(db_session, idx: int) -> PortLookup:
    port = PortLookup(
        id=idx,
        port_code=f"PRT{idx:03d}",
        port_name=f"Port {idx}",
        country="US",
        is_active=True,
    )
    db_session.add(port)
    db_session.commit()
    return port


def test_metadata_users_data_pagination(client, db_session):
    _seed_user(db_session, 1)
    _seed_user(db_session, 2)
    _seed_user(db_session, 3)

    response = client.get("/metadata/users/data", params={"skip": 1, "limit": 1})
    assert response.status_code == 200
    payload = response.json()

    assert payload["total"] == 3
    assert payload["skip"] == 1
    assert payload["limit"] == 1
    assert len(payload["items"]) == 1
    # Ordered by PK desc: [3,2,1], so skip=1 returns id=2.
    assert payload["items"][0]["id"] == 2

    filtered = client.get("/metadata/users/data", params={"username": "user1"})
    assert filtered.status_code == 200
    filtered_payload = filtered.json()
    assert filtered_payload["total"] == 1
    assert len(filtered_payload["items"]) == 1
    assert filtered_payload["items"][0]["username"] == "user1"


def test_customer_forwarders_paged_list(client, db_session):
    _seed_roles(db_session)
    customer = _seed_customer(db_session, 1)
    p1 = _seed_partner(db_session, 1)
    p2 = _seed_partner(db_session, 2)
    p3 = _seed_partner(db_session, 3)

    db_session.add_all(
        [
            CustomerForwarder(
                id=1,
                customer_id=customer.id,
                forwarder_id=p1.id,
                deletion_indicator=False,
            ),
            CustomerForwarder(
                id=2,
                customer_id=customer.id,
                forwarder_id=p2.id,
                deletion_indicator=True,
            ),
            CustomerForwarder(
                id=3,
                customer_id=customer.id,
                forwarder_id=p3.id,
                deletion_indicator=False,
            ),
        ]
    )
    db_session.commit()

    response = client.get(
        "/customer-forwarders/paged/list",
        params={"skip": 0, "limit": 1, "deletion_indicator": "false"},
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload["total"] == 2
    assert len(payload["items"]) == 1
    assert payload["items"][0]["id"] == 3

    second_page = client.get(
        "/customer-forwarders/paged/list",
        params={"skip": 1, "limit": 1, "deletion_indicator": "false"},
    )
    assert second_page.status_code == 200
    assert second_page.json()["items"][0]["id"] == 1


def test_forwarder_ports_paged_list(client, db_session):
    _seed_roles(db_session)
    forwarder = _seed_partner(db_session, 1)
    port1 = _seed_port(db_session, 1)
    port2 = _seed_port(db_session, 2)
    port3 = _seed_port(db_session, 3)

    db_session.add_all(
        [
            ForwarderPortMap(
                id=1,
                forwarder_id=forwarder.id,
                port_id=port1.id,
                deletion_indicator=False,
            ),
            ForwarderPortMap(
                id=2,
                forwarder_id=forwarder.id,
                port_id=port2.id,
                deletion_indicator=True,
            ),
            ForwarderPortMap(
                id=3,
                forwarder_id=forwarder.id,
                port_id=port3.id,
                deletion_indicator=False,
            ),
        ]
    )
    db_session.commit()

    response = client.get(
        "/forwarder-port-map/paged/list",
        params={"skip": 0, "limit": 1, "deletion_indicator": "false"},
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload["total"] == 2
    assert len(payload["items"]) == 1
    assert payload["items"][0]["id"] == 3


def test_user_partner_paged_list(client, db_session):
    _seed_roles(db_session)
    user = _seed_user(db_session, 1)
    p1 = _seed_partner(db_session, 1)
    p2 = _seed_partner(db_session, 2)
    p3 = _seed_partner(db_session, 3)

    db_session.add_all(
        [
            UserPartnerLink(
                id=1,
                user_email=user.email,
                partner_id=p1.id,
                deletion_indicator=False,
            ),
            UserPartnerLink(
                id=2,
                user_email=user.email,
                partner_id=p2.id,
                deletion_indicator=True,
            ),
            UserPartnerLink(
                id=3,
                user_email=user.email,
                partner_id=p3.id,
                deletion_indicator=False,
            ),
        ]
    )
    db_session.commit()

    response = client.get(
        "/user-partners/paged/list",
        params={"skip": 0, "limit": 1, "deletion_indicator": "false"},
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload["total"] == 2
    assert len(payload["items"]) == 1
    assert payload["items"][0]["id"] == 3


def test_user_customer_paged_list(client, db_session):
    _seed_roles(db_session)
    user = _seed_user(db_session, 1)
    c1 = _seed_customer(db_session, 1)
    c2 = _seed_customer(db_session, 2)
    c3 = _seed_customer(db_session, 3)

    db_session.add_all(
        [
            UserCustomerLink(
                id=1,
                user_email=user.email,
                customer_id=c1.id,
                deletion_indicator=False,
            ),
            UserCustomerLink(
                id=2,
                user_email=user.email,
                customer_id=c2.id,
                deletion_indicator=True,
            ),
            UserCustomerLink(
                id=3,
                user_email=user.email,
                customer_id=c3.id,
                deletion_indicator=False,
            ),
        ]
    )
    db_session.commit()

    response = client.get(
        "/user-customers/paged/list",
        params={"skip": 0, "limit": 1, "deletion_indicator": "false"},
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload["total"] == 2
    assert len(payload["items"]) == 1
    assert payload["items"][0]["id"] == 3
