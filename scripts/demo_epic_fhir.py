#!/usr/bin/env python3
"""
Epic FHIR Demo Script.

Demonstrates Epic FHIR client functionality with mocked responses.
Useful for testing without real Epic credentials.

Usage:
    # Run demo with mocked data
    python scripts/demo_epic_fhir.py

    # Run with real Epic sandbox (requires credentials)
    python scripts/demo_epic_fhir.py --real
"""

import argparse
import asyncio
import sys
from pathlib import Path
from unittest.mock import AsyncMock, Mock, patch

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from fhir.resources.condition import Condition
from fhir.resources.encounter import Encounter
from fhir.resources.observation import Observation
from fhir.resources.patient import Patient

from src.python.mcp_servers.epic_fhir.client import EpicFHIRClient
from src.python.utils.logging import get_logger

logger = get_logger(__name__)


# Mock patient data
MOCK_PATIENT = {
    "resourceType": "Patient",
    "id": "demo.patient123",
    "identifier": [
        {"system": "urn:oid:1.2.840.114350", "value": "MRN123456"}
    ],
    "name": [
        {
            "use": "official",
            "family": "Argonaut",
            "given": ["Jason"],
            "text": "Jason Argonaut",
        }
    ],
    "gender": "male",
    "birthDate": "1980-01-15",
    "address": [
        {
            "use": "home",
            "line": ["123 Main St"],
            "city": "Springfield",
            "state": "IL",
            "postalCode": "62701",
        }
    ],
}

MOCK_ENCOUNTERS = {
    "resourceType": "Bundle",
    "type": "searchset",
    "entry": [
        {
            "resource": {
                "resourceType": "Encounter",
                "id": "enc123",
                "status": "finished",
                "class": {
                    "system": "http://terminology.hl7.org/CodeSystem/v3-ActCode",
                    "code": "AMB",
                    "display": "ambulatory",
                },
                "type": [
                    {
                        "coding": [
                            {
                                "system": "http://www.ama-assn.org/go/cpt",
                                "code": "99214",
                                "display": "Office Visit - Level 4",
                            }
                        ]
                    }
                ],
                "subject": {"reference": "Patient/demo.patient123"},
                "period": {
                    "start": "2024-01-15T09:00:00Z",
                    "end": "2024-01-15T09:30:00Z",
                },
            }
        }
    ],
}

MOCK_CONDITIONS = {
    "resourceType": "Bundle",
    "type": "searchset",
    "entry": [
        {
            "resource": {
                "resourceType": "Condition",
                "id": "cond123",
                "clinicalStatus": {
                    "coding": [
                        {
                            "system": "http://terminology.hl7.org/CodeSystem/condition-clinical",
                            "code": "active",
                        }
                    ],
                    "text": "Active",
                },
                "code": {
                    "coding": [
                        {"system": "http://hl7.org/fhir/sid/icd-10-cm", "code": "E11.9"}
                    ],
                    "text": "Type 2 diabetes mellitus without complications",
                },
                "subject": {"reference": "Patient/demo.patient123"},
                "recordedDate": "2024-01-01",
            }
        },
        {
            "resource": {
                "resourceType": "Condition",
                "id": "cond124",
                "clinicalStatus": {
                    "coding": [
                        {
                            "system": "http://terminology.hl7.org/CodeSystem/condition-clinical",
                            "code": "active",
                        }
                    ],
                    "text": "Active",
                },
                "code": {
                    "coding": [
                        {"system": "http://hl7.org/fhir/sid/icd-10-cm", "code": "I10"}
                    ],
                    "text": "Essential (primary) hypertension",
                },
                "subject": {"reference": "Patient/demo.patient123"},
                "recordedDate": "2023-06-15",
            }
        },
    ],
}

MOCK_OBSERVATIONS = {
    "resourceType": "Bundle",
    "type": "searchset",
    "entry": [
        {
            "resource": {
                "resourceType": "Observation",
                "id": "obs123",
                "status": "final",
                "category": [
                    {
                        "coding": [
                            {
                                "system": "http://terminology.hl7.org/CodeSystem/observation-category",
                                "code": "laboratory",
                            }
                        ]
                    }
                ],
                "code": {
                    "coding": [
                        {"system": "http://loinc.org", "code": "2339-0"}
                    ],
                    "text": "Glucose",
                },
                "subject": {"reference": "Patient/demo.patient123"},
                "effectiveDateTime": "2024-01-15T09:00:00Z",
                "valueQuantity": {
                    "value": 95,
                    "unit": "mg/dL",
                    "system": "http://unitsofmeasure.org",
                    "code": "mg/dL",
                },
                "interpretation": [
                    {
                        "coding": [
                            {
                                "system": "http://terminology.hl7.org/CodeSystem/v3-ObservationInterpretation",
                                "code": "N",
                                "display": "Normal",
                            }
                        ]
                    }
                ],
            }
        }
    ],
}


async def demo_with_mocked_data():
    """Run demo with mocked Epic FHIR responses."""
    print("\n" + "=" * 60)
    print("EPIC FHIR DEMO - Mocked Data")
    print("=" * 60)

    # Create client (won't actually connect)
    client = EpicFHIRClient(
        base_url="https://demo.epic.com/fhir",
        client_id="demo_client",
    )

    # Mock authentication
    client._access_token = "demo_token"

    print("\n1. Testing Patient Retrieval")
    print("-" * 60)

    # Mock HTTP response
    mock_response = Mock()
    mock_response.json.return_value = MOCK_PATIENT
    mock_response.raise_for_status = Mock()

    with patch.object(client.http_client, "request", return_value=mock_response):
        patient = await client.get_patient("demo.patient123")

        print(f"✓ Patient Retrieved:")
        print(f"  ID: {patient.id}")
        print(f"  Name: {patient.name[0].text if patient.name else 'N/A'}")
        print(f"  DOB: {patient.birthDate}")
        print(f"  Gender: {patient.gender}")
        if patient.address:
            addr = patient.address[0]
            print(f"  Address: {addr.line[0] if addr.line else ''}, {addr.city}, {addr.state}")

    print("\n2. Testing Encounter Retrieval")
    print("-" * 60)

    mock_response.json.return_value = MOCK_ENCOUNTERS

    with patch.object(client.http_client, "request", return_value=mock_response):
        encounters = await client.get_patient_encounters("demo.patient123")

        print(f"✓ Found {len(encounters)} encounter(s):")
        for enc in encounters:
            print(f"  - ID: {enc.id}")
            print(f"    Status: {enc.status}")
            print(f"    Type: {enc.class_.display if enc.class_ else 'N/A'}")
            if enc.period:
                print(f"    Date: {enc.period.start}")

    print("\n3. Testing Condition (Diagnosis) Retrieval")
    print("-" * 60)

    mock_response.json.return_value = MOCK_CONDITIONS

    with patch.object(client.http_client, "request", return_value=mock_response):
        conditions = await client.get_patient_conditions("demo.patient123")

        print(f"✓ Found {len(conditions)} condition(s):")
        for cond in conditions:
            print(f"  - {cond.code.text if cond.code else 'N/A'}")
            if cond.code and cond.code.coding:
                print(f"    Code: {cond.code.coding[0].code}")
            print(f"    Status: {cond.clinicalStatus.text if cond.clinicalStatus else 'N/A'}")
            print(f"    Recorded: {cond.recordedDate if hasattr(cond, 'recordedDate') else 'N/A'}")

    print("\n4. Testing Observation (Lab) Retrieval")
    print("-" * 60)

    mock_response.json.return_value = MOCK_OBSERVATIONS

    with patch.object(client.http_client, "request", return_value=mock_response):
        observations = await client.get_patient_observations(
            "demo.patient123",
            category="laboratory",
        )

        print(f"✓ Found {len(observations)} observation(s):")
        for obs in observations:
            print(f"  - {obs.code.text if obs.code else 'N/A'}")
            if hasattr(obs, "valueQuantity") and obs.valueQuantity:
                print(f"    Value: {obs.valueQuantity.value} {obs.valueQuantity.unit}")
            if obs.interpretation:
                print(f"    Interpretation: {obs.interpretation[0].coding[0].display}")
            print(f"    Date: {obs.effectiveDateTime if hasattr(obs, 'effectiveDateTime') else 'N/A'}")

    await client.close()

    print("\n" + "=" * 60)
    print("DEMO COMPLETE")
    print("=" * 60)
    print("\nTo test with real Epic sandbox:")
    print("1. Complete setup in docs/epic_fhir_setup.md")
    print("2. Run: python scripts/demo_epic_fhir.py --real")


async def demo_with_real_epic():
    """Run demo with real Epic sandbox."""
    print("\n" + "=" * 60)
    print("EPIC FHIR DEMO - Real Epic Sandbox")
    print("=" * 60)

    try:
        # Epic sandbox test patient ID
        TEST_PATIENT_ID = "erXuFYUfucBZaryVksYEcMg3"  # Jason Argonaut

        async with EpicFHIRClient() as client:
            print("\n1. Authenticating with Epic...")
            print("-" * 60)

            try:
                await client.authenticate()
                print("✓ Authentication successful!")
            except Exception as e:
                print(f"✗ Authentication failed: {e}")
                print("\nPlease check:")
                print("  - EPIC_CLIENT_ID in .env")
                print("  - EPIC_PRIVATE_KEY_PATH points to valid key")
                print("  - Public key uploaded to Epic App Gallery")
                return

            print("\n2. Retrieving Patient...")
            print("-" * 60)

            patient = await client.get_patient(TEST_PATIENT_ID)
            print(f"✓ Patient Retrieved:")
            print(f"  ID: {patient.id}")
            print(f"  Name: {patient.name[0].text if patient.name else 'N/A'}")
            print(f"  DOB: {patient.birthDate}")
            print(f"  Gender: {patient.gender}")

            print("\n3. Retrieving Encounters...")
            print("-" * 60)

            encounters = await client.get_patient_encounters(TEST_PATIENT_ID, limit=5)
            print(f"✓ Found {len(encounters)} encounter(s)")
            for i, enc in enumerate(encounters[:3], 1):
                print(f"  {i}. {enc.id}: {enc.status}")

            print("\n4. Retrieving Conditions...")
            print("-" * 60)

            conditions = await client.get_patient_conditions(TEST_PATIENT_ID, limit=10)
            print(f"✓ Found {len(conditions)} condition(s)")
            for i, cond in enumerate(conditions[:5], 1):
                print(f"  {i}. {cond.code.text if cond.code else 'N/A'}")

            print("\n5. Retrieving Observations...")
            print("-" * 60)

            observations = await client.get_patient_observations(
                TEST_PATIENT_ID,
                category="laboratory",
                limit=5,
            )
            print(f"✓ Found {len(observations)} observation(s)")
            for i, obs in enumerate(observations[:3], 1):
                value = "N/A"
                if hasattr(obs, "valueQuantity") and obs.valueQuantity:
                    value = f"{obs.valueQuantity.value} {obs.valueQuantity.unit}"
                print(f"  {i}. {obs.code.text if obs.code else 'N/A'}: {value}")

            print("\n" + "=" * 60)
            print("DEMO COMPLETE - Successfully connected to Epic!")
            print("=" * 60)

    except Exception as e:
        print(f"\n✗ Error: {e}")
        print("\nTroubleshooting:")
        print("  1. Check docs/epic_fhir_setup.md for setup instructions")
        print("  2. Verify .env configuration")
        print("  3. Test authentication first")


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Epic FHIR Demo - Test Epic integration",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )

    parser.add_argument(
        "--real",
        action="store_true",
        help="Use real Epic sandbox (requires credentials)",
    )

    args = parser.parse_args()

    if args.real:
        print("\n⚠️  Real Epic Sandbox Mode")
        print("This requires valid Epic credentials configured in .env")
        asyncio.run(demo_with_real_epic())
    else:
        print("\n📝 Mocked Data Mode (No credentials required)")
        asyncio.run(demo_with_mocked_data())


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\nDemo interrupted by user.")
        sys.exit(0)
    except Exception as e:
        print(f"\n✗ Fatal error: {e}")
        sys.exit(1)
