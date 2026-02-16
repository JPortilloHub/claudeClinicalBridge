# CPT Code Licensing Requirements

## Overview

Current Procedural Terminology (CPT) codes are **proprietary** and copyrighted by the **American Medical Association (AMA)**. Unlike ICD-10-CM codes (which are published by CDC and are in the public domain), CPT codes require a license for most uses.

## Development & Testing Use

### ✅ Permitted for This Project

For **development, research, and demonstration purposes**, this project uses a **limited sample dataset** of approximately 50 common CPT codes. This falls under fair use for:

- Educational purposes
- Research and development
- Non-commercial demonstration
- Limited code examples in documentation

### ⚠️ Sample Dataset Limitations

The sample CPT dataset included in `data/cpt/sample_cpt_codes.json` contains:
- ~50 commonly used CPT codes
- Representative codes across major categories (E&M, Lab, Radiology, Surgery)
- Sufficient for testing semantic search and agent functionality
- **NOT comprehensive** for production use

## Production Deployment Requirements

### 🚫 Production Use Requires AMA License

For any **production deployment** with real patient data or clinical use, you **MUST** obtain a license from the AMA. This includes:

1. **Commercial Use** - Any revenue-generating application
2. **Clinical Use** - Integration with real EHR systems or clinical workflows
3. **Billing Systems** - Integration with medical billing or claims processing
4. **Comprehensive Datasets** - Using the full CPT code set (10,000+ codes)

### How to Obtain a CPT License

**Contact the AMA:**
- Website: https://www.ama-assn.org/practice-management/cpt/cpt-licensing
- Email: cptlicense@ama-assn.org
- Phone: (312) 464-5022

**License Types:**
- **Data File License** - For using CPT codes in software
- **End-User License** - For displaying CPT codes to users
- **Distribution License** - For distributing CPT codes with your application

**Pricing:**
- Varies based on use case, number of users, and revenue
- Typically requires annual renewal
- Contact AMA for specific pricing

## HCPCS Alternative

### Public Domain Option

As an alternative to CPT codes, consider **HCPCS Level II codes**, which are:

- ✅ **Public domain** (published by CMS)
- ✅ **No licensing required**
- ✅ **Cover many procedures** (especially DME, supplies, services not in CPT)
- ⚠️ **Less comprehensive** than CPT for physician services
- ⚠️ **Different code structure** (alphanumeric vs numeric)

**HCPCS Codes Cover:**
- Durable Medical Equipment (DME)
- Prosthetics and Orthotics
- Supplies and Medications
- Ambulance Services
- Some procedures not covered by CPT

**Source:** https://www.cms.gov/medicare/coding-billing/healthcare-common-procedure-system

### Hybrid Approach

Many production systems use a **hybrid approach**:
- **CPT codes** (licensed from AMA) for physician services, E&M, surgery
- **HCPCS codes** (free) for equipment, supplies, certain services

## Compliance Checklist

### Development Phase ✅
- [x] Using limited sample dataset (<100 codes)
- [x] Non-commercial, educational purpose
- [x] Clearly documented as sample data
- [x] Disclaimer in README.md

### Before Production Deployment ⚠️
- [ ] Obtain AMA CPT license (or use HCPCS alternative)
- [ ] Sign license agreement and pay fees
- [ ] Implement licensed CPT code dataset
- [ ] Add AMA copyright notice to application
- [ ] Comply with license terms (usage restrictions, attribution)
- [ ] Set up annual license renewal process

## Copyright Notice

When using licensed CPT codes, you **must** include this notice:

```
CPT® Copyright [YEAR] American Medical Association. All rights reserved.
CPT® is a registered trademark of the American Medical Association.
```

## Legal Disclaimer

⚠️ **This project is for development and research purposes only.**

The sample CPT codes included in this repository are:
- Limited in scope (representative examples only)
- Provided for development, testing, and demonstration
- **NOT licensed for production use with real patient data**

For production deployment:
1. Obtain proper CPT licensing from the AMA
2. Replace sample dataset with licensed CPT code set
3. Comply with all AMA license terms and conditions
4. Consult with legal counsel regarding healthcare data regulations

## References

1. **AMA CPT Licensing**
   - https://www.ama-assn.org/practice-management/cpt/cpt-licensing

2. **CMS HCPCS Codes** (Public Domain Alternative)
   - https://www.cms.gov/medicare/coding-billing/healthcare-common-procedure-system

3. **ICD-10-CM Codes** (Public Domain for Diagnosis Codes)
   - https://www.cdc.gov/nchs/icd/icd-10-cm.htm

4. **ONC Health IT Certification** (If pursuing certification)
   - https://www.healthit.gov/topic/certification-ehrs/certification-health-it

## Frequently Asked Questions

### Q: Can I use CPT codes for free in my app?
**A:** No. CPT codes are copyrighted and require a license from the AMA for most uses. Fair use exceptions exist for education and limited research, but production use requires licensing.

### Q: What happens if I use CPT codes without a license?
**A:** The AMA actively enforces their copyright. Unlicensed use can result in:
- Cease and desist letters
- Legal action for copyright infringement
- Financial penalties
- Requirement to remove CPT codes from your application

### Q: How much does a CPT license cost?
**A:** Pricing varies widely based on:
- Type of use (clinical, billing, informational)
- Number of end users
- Revenue from the application
- Distribution model

Contact the AMA for specific pricing for your use case.

### Q: Are there free alternatives to CPT codes?
**A:** Yes:
- **HCPCS Level II codes** (public domain, published by CMS)
- **ICD-10-PCS codes** (for inpatient procedures, public domain)
- However, CPT remains the standard for most outpatient physician services

### Q: Does this project include a CPT license?
**A:** No. This project includes only a limited sample dataset for development purposes. You must obtain your own license for production use.

---

**Last Updated:** February 2026
**Maintained By:** Claude Clinical Bridge Project
**Review Annually** for licensing requirement changes
