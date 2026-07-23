# Open Questions

These questions remain unresolved after normalizing the BitonX specification.

## Product Scope

1. Should the first build target only architectural floor plans, or include structural drawings as well?
2. Is the MVP expected to support multi-page PDF projects, or one drawing at a time?
3. Should a final BOQ require explicit engineer approval?
4. Should users be able to manually edit geometry, quantities, and unit prices?

## Engineering Rules

1. Which rule pack comes first: generic metric, Morocco, France, Eurocode, ACI, ASTM, or GCC?
2. What are the default wall heights, slab thicknesses, material densities, and waste factors when the drawing omits them?
3. Which units and currencies are required for the first release?
4. Should assumptions appear as report warnings or block finalization?

## AI And Data

1. Should MVP use pretrained/baseline models first, or begin with full training on CubiCasa5K and ResPlan?
2. What minimum accuracy thresholds are required for OCR, detection, segmentation, and quantities?
3. Are proprietary drawings available for validation?
4. Should uploaded customer drawings be retained for future model training, and under what consent policy?

## Infrastructure

1. Is local Docker Compose the only required Phase 2 environment?
2. Which production cloud provider should Kubernetes target later?
3. Will GPU inference be required in production for MVP?
4. What file size, page count, and processing-time limits should be enforced?

## Security And Compliance

1. Is organization-level multi-tenancy required in V1?
2. What data retention period applies to uploaded drawings and reports?
3. Are uploaded files required to be encrypted at rest?
4. Is malware scanning required before storing files permanently?

## Reporting

1. Which report format is highest priority: PDF, Excel, CSV, or JSON?
2. What BOQ format or regional standard should the output follow?
3. Should reports include confidence thresholds and warnings by default?
4. Should report version history be immutable?

