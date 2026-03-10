# TODO - Inventory Highlighting Feature

## Task
Add explicit highlighting for AERMAT 9000 colors and CARPET material types in inventory response

## Steps
1. [x] Analyze codebase and understand existing inventory logic
2. [x] Create helper function `format_highlighted_name()` in erp.py
3. [x] Add `highlighted_name` field to CarpetItem model
4. [x] Update `get_inventory` endpoint to use highlighted names
5. [x] Test the implementation

## Details
- AERMAT 9000: Highlight color (GREY/BLUE) explicitly in title
- CARPET: Highlight material type (WOVEN/ECONYL RIPS) to prevent wrong material selection

## Implementation Summary
- Added `highlighted_name` field to `CarpetItem` Pydantic model
- Created `format_highlighted_name()` helper function that:
  - For AERMAT 9000: Returns "ProductName [COLOR: GREY]" or "ProductName [COLOR: BLUE]"
  - For CARPET: Returns "ProductName [MATERIAL: WOVEN]" or "ProductName [MATERIAL: ECONYL RIPS]"
- Updated `/inventory` endpoint to populate `highlighted_name` for all items

