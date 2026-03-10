-- Aviation Inventory Table
-- This script creates the aviation_inventory table for the Aviation ERP system

CREATE TABLE IF NOT EXISTS aviation_inventory (
    part_number TEXT PRIMARY KEY,
    description TEXT NOT NULL,
    opening_stock NUMERIC NOT NULL DEFAULT 0,
    uom TEXT NOT NULL,
    cont NUMERIC NOT NULL DEFAULT 0,
    sold_stock NUMERIC NOT NULL DEFAULT 0,
    in_house NUMERIC NOT NULL DEFAULT 0,
    current_stock NUMERIC NOT NULL,
    batch_no TEXT,
    dom DATE,
    category TEXT NOT NULL
);

-- Create indexes for common queries
CREATE INDEX IF NOT EXISTS idx_aviation_inventory_category ON aviation_inventory(category);
CREATE INDEX IF NOT EXISTS idx_aviation_inventory_uom ON aviation_inventory(uom);
CREATE INDEX IF NOT EXISTS idx_aviation_inventory_current_stock ON aviation_inventory(current_stock);

-- Insert sample data (optional - for testing)
-- INSERT INTO aviation_inventory (part_number, description, opening_stock, uom, cont, sold_stock, in_house, current_stock, batch_no, dom, category)
-- VALUES 
-- ('113-22-633B-3-033', 'EPOXY PRIMER 6KG', 10, 'KG', 2, 4, 6, 6, 'BATCH001', '2024-01-15', 'Paint'),
-- ('470-10-9100-9-003', 'WHITE TOPCOAT 10KG', 15, 'KG', 3, 5, 10, 10, 'BATCH002', '2024-02-20', 'Paint');

-- View to see low stock items
CREATE OR REPLACE VIEW view_low_stock_inventory AS
SELECT 
    part_number,
    description,
    category,
    current_stock,
    uom
FROM aviation_inventory
WHERE current_stock <= 5;

-- View for Paint category
CREATE OR REPLACE VIEW view_paint_inventory AS
SELECT * FROM aviation_inventory WHERE category = 'Paint';

-- View for Carpet category
CREATE OR REPLACE VIEW view_carpet_inventory AS
SELECT * FROM aviation_inventory WHERE category = 'Carpet';

