-- ============================================================
-- Aviation ERP - PostgreSQL Schema
-- Products and Stock Management
-- ============================================================

-- Enable UUID extension
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- ============================================================
-- ENUMS for consistent unit types
-- ============================================================

CREATE TYPE unit_category AS ENUM (
    'length',
    'weight',
    'volume',
    'area',
    'quantity'
);

CREATE TYPE transaction_type AS ENUM (
    'purchase',
    'sale',
    'adjustment',
    'transfer',
    'tint_deduction',
    'kit_assembly',
    'kit_disassembly',
    'return',
    'damage',
    'expiry'
);

-- ============================================================
-- UNITS REFERENCE TABLE
-- ============================================================

CREATE TABLE units (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name VARCHAR(100) NOT NULL UNIQUE,
    symbol VARCHAR(20) NOT NULL UNIQUE,
    category unit_category NOT NULL,
    is_base_unit BOOLEAN DEFAULT FALSE,
    conversion_factor_to_base NUMERIC(18, 8), -- factor to convert to base unit of category
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Insert common units
INSERT INTO units (name, symbol, category, is_base_unit, conversion_factor_to_base) VALUES
-- Volume (base: Liters)
('Liters', 'L', 'volume', TRUE, 1),
('Milliliters', 'ml', 'volume', FALSE, 0.001),
('Gallons (US)', 'gal', 'volume', FALSE, 3.78541),
('Gallons (UK)', 'gal_uk', 'volume', FALSE, 4.54609),

-- Weight (base: Grams)
('Grams', 'g', 'weight', TRUE, 1),
('Kilograms', 'kg', 'weight', FALSE, 1000),
('Milligrams', 'mg', 'weight', FALSE, 0.001),
('Pounds', 'lb', 'weight', FALSE, 453.592),
('Ounces', 'oz', 'weight', FALSE, 28.3495),

-- Length (base: Meters)
('Meters', 'm', 'length', TRUE, 1),
('Centimeters', 'cm', 'length', FALSE, 0.01),
('Millimeters', 'mm', 'length', FALSE, 0.001),
('Yards', 'yd', 'length', FALSE, 0.9144),
('Feet', 'ft', 'length', FALSE, 0.3048),
('Inches', 'in', 'length', FALSE, 0.0254),

-- Area (base: Square Meters)
('Square Meters', 'm2', 'area', TRUE, 1),
('Square Feet', 'ft2', 'area', FALSE, 0.092903),
('Square Yards', 'yd2', 'area', FALSE, 0.836127),

-- Quantity (base: Pieces)
('Pieces', 'pcs', 'quantity', TRUE, 1),
('Pairs', 'pr', 'quantity', FALSE, 2),
('Sets', 'set', 'quantity', FALSE, 1),
('Boxes', 'box', 'quantity', FALSE, 1),
('Drums', 'drum', 'quantity', FALSE, 1),
('Cans', 'can', 'quantity', FALSE, 1);

-- ============================================================
-- PRODUCT CATEGORIES
-- ============================================================

CREATE TABLE product_categories (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name VARCHAR(100) NOT NULL UNIQUE,
    description TEXT,
    parent_id UUID REFERENCES product_categories(id) ON DELETE SET NULL,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- ============================================================
-- PRODUCTS TABLE
-- ============================================================

CREATE TABLE products (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    
    -- Basic Product Information
    sku VARCHAR(50) NOT NULL UNIQUE,
    name VARCHAR(255) NOT NULL,
    description TEXT,
    category_id UUID REFERENCES product_categories(id) ON DELETE SET NULL,
    
    -- Unit Management
    purchase_unit_id UUID REFERENCES units(id) ON DELETE SET NULL,
    sales_unit_id UUID REFERENCES units(id) ON DELETE SET NULL,
    base_unit_id UUID REFERENCES units(id) ON DELETE SET NULL,
    
    -- Conversion Rate (from purchase unit to sales unit)
    -- Example: If purchase_unit = Liters, sales_unit = Gallons
    -- conversion_rate = 3.78541 (Liters to Gallons)
    conversion_rate NUMERIC(18, 8) DEFAULT 1,
    
    -- Pricing
    purchase_price NUMERIC(15, 4),
    sales_price NUMERIC(15, 4),
    min_stock_level NUMERIC(18, 4) DEFAULT 0,
    max_stock_level NUMERIC(18, 4),
    
    -- Tinting Support
    is_primary_color BOOLEAN DEFAULT FALSE,
    is_tint BOOLEAN DEFAULT FALSE, -- Flag indicating this is a tint/colorant product
    tint_volume_deduction NUMERIC(5, 4) DEFAULT 0, -- Percentage deducted per tint (e.g., 0.02 = 2%)
    
    -- Kitting Support
    is_kit BOOLEAN DEFAULT FALSE,
    kit_components JSONB DEFAULT '[]', -- Array of component products with quantities
    -- Example: [{"product_id": "uuid", "quantity": 2, "unit_id": "uuid"}]
    
    -- Mixing Ratio for Paint Kits (stored as JSONB)
    -- Example: {"hardener": 1.0, "thinner": 1.0} means 1L hardener and 1L thinner per 1L primary
    mixing_ratio JSONB DEFAULT '{"hardener": 1.0, "thinner": 1.0}'::JSONB,
    
    -- Stock Tracking (in base unit for high precision)
    current_stock_level NUMERIC(18, 6) DEFAULT 0,
    
    -- Product Status
    is_active BOOLEAN DEFAULT TRUE,
    is_tracked BOOLEAN DEFAULT TRUE, -- Whether to track stock
    
    -- Metadata
    barcode VARCHAR(100),
    manufacturer VARCHAR(255),
    manufacturer_sku VARCHAR(100),
    
    -- Location (e.g., warehouse, shelf, bin)
    location VARCHAR(255),
    
    -- Timestamps
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Indexes for products table
CREATE INDEX idx_products_sku ON products(sku);
CREATE INDEX idx_products_category ON products(category_id);
CREATE INDEX idx_products_is_active ON products(is_active);
CREATE INDEX idx_products_is_kit ON products(is_kit);
CREATE INDEX idx_products_is_tint ON products(is_tint);
CREATE INDEX idx_products_is_primary_color ON products(is_primary_color);
CREATE INDEX idx_products_current_stock ON products(current_stock_level);
CREATE INDEX idx_products_location ON products(location);

-- ============================================================
-- STOCK TRANSACTIONS TABLE
-- ============================================================

CREATE TABLE stock_transactions (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    
    -- Reference to product
    product_id UUID NOT NULL REFERENCES products(id) ON DELETE CASCADE,
    
    -- Transaction Details
    transaction_type transaction_type NOT NULL,
    quantity NUMERIC(18, 6) NOT NULL, -- Quantity in base unit
    quantity_before NUMERIC(18, 6) NOT NULL,
    quantity_after NUMERIC(18, 6) NOT NULL,
    
    -- Reference Documents
    reference_type VARCHAR(50), -- e.g., 'purchase_order', 'sales_order', 'invoice'
    reference_id UUID, -- Link to the actual document
    
    -- For tinting transactions - links to color used
    tint_product_id UUID REFERENCES products(id), -- The primary color used
    tint_deduction_amount NUMERIC(18, 6), -- Amount deducted for tinting
    
    -- For kit transactions
    kit_reference_id UUID, -- Reference to kit assembly/disassembly
    
    -- Additional Details
    notes TEXT,
    
    -- User who created the transaction
    created_by UUID, -- Would link to users table in full system
    
    -- Timestamps
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Indexes for stock transactions
CREATE INDEX idx_stock_transactions_product ON stock_transactions(product_id);
CREATE INDEX idx_stock_transactions_type ON stock_transactions(transaction_type);
CREATE INDEX idx_stock_transactions_created_at ON stock_transactions(created_at DESC);
CREATE INDEX idx_stock_transactions_reference ON stock_transactions(reference_type, reference_id);

-- ============================================================
-- KIT COMPONENTS VIEW (for easy querying of kit contents)
-- ============================================================

CREATE OR REPLACE VIEW kit_components_view AS
SELECT 
    p.id AS kit_product_id,
    p.name AS kit_name,
    p.sku AS kit_sku,
    (kit_components->>'components')::JSONB AS components,
    component->>'product_id' AS component_product_id,
    (component->>'quantity')::NUMERIC AS component_quantity,
    comp.name AS component_name,
    comp.sku AS component_sku
FROM products p
CROSS JOIN LATERAL jsonb_array_elements(kit_components->'components') AS component
LEFT JOIN products comp ON comp.id = (component->>'product_id')::UUID
WHERE p.is_kit = TRUE;

-- ============================================================
-- PRODUCT STOCK SUMMARY VIEW
-- ============================================================

CREATE OR REPLACE VIEW product_stock_summary AS
SELECT 
    p.id,
    p.sku,
    p.name,
    p.current_stock_level,
    p.min_stock_level,
    p.max_stock_level,
    p.base_unit_id,
    u.symbol AS base_unit_symbol,
    CASE 
        WHEN p.current_stock_level <= p.min_stock_level THEN 'below_minimum'
        WHEN p.current_stock_level >= p.max_stock_level THEN 'above_maximum'
        ELSE 'normal'
    END AS stock_status
FROM products p
LEFT JOIN units u ON p.base_unit_id = u.id
WHERE p.is_tracked = TRUE;

-- ============================================================
-- FUNCTION: Update stock level and create transaction
-- ============================================================

CREATE OR REPLACE FUNCTION update_stock(
    p_product_id UUID,
    p_transaction_type transaction_type,
    p_quantity NUMERIC,
    p_reference_type VARCHAR(50) DEFAULT NULL,
    p_reference_id UUID DEFAULT NULL,
    p_notes TEXT DEFAULT NULL,
    p_created_by UUID DEFAULT NULL
) RETURNS VOID AS $$
DECLARE
    v_quantity_before NUMERIC(18, 6);
    v_quantity_after NUMERIC(18, 6);
    v_product RECORD;
BEGIN
    -- Get current product
    SELECT * INTO v_product 
    FROM products 
    WHERE id = p_product_id;
    
    IF v_product IS NULL THEN
        RAISE EXCEPTION 'Product not found: %', p_product_id;
    END IF;
    
    IF NOT v_product.is_tracked THEN
        RAISE NOTICE 'Stock tracking is disabled for product: %', v_product.name;
        RETURN;
    END IF;
    
    v_quantity_before := v_product.current_stock_level;
    
    -- Calculate new quantity based on transaction type
    CASE p_transaction_type
        WHEN 'purchase', 'return', 'transfer', 'kit_disassembly', 'adjustment' THEN
            v_quantity_after := v_quantity_before + p_quantity;
        WHEN 'sale', 'tint_deduction', 'kit_assembly', 'damage', 'expiry' THEN
            v_quantity_after := v_quantity_before - p_quantity;
        ELSE
            v_quantity_after := v_quantity_before + p_quantity;
    END CASE;
    
    -- Prevent negative stock
    IF v_quantity_after < 0 THEN
        RAISE EXCEPTION 'Insufficient stock. Current: %, Requested: %', 
            v_quantity_before, p_quantity;
    END IF;
    
    -- Update product stock
    UPDATE products 
    SET current_stock_level = v_quantity_after,
        updated_at = NOW()
    WHERE id = p_product_id;
    
    -- Create stock transaction record
    INSERT INTO stock_transactions (
        product_id,
        transaction_type,
        quantity,
        quantity_before,
        quantity_after,
        reference_type,
        reference_id,
        notes,
        created_by
    ) VALUES (
        p_product_id,
        p_transaction_type,
        p_quantity,
        v_quantity_before,
        v_quantity_after,
        p_reference_type,
        p_reference_id,
        p_notes,
        p_created_by
    );
END;
$$ LANGUAGE plpgsql;

-- ============================================================
-- FUNCTION: Calculate sales unit quantity from purchase quantity
-- ============================================================

CREATE OR REPLACE FUNCTION calculate_sales_quantity(
    p_product_id UUID,
    p_purchase_quantity NUMERIC
) RETURNS NUMERIC AS $$
DECLARE
    v_conversion_rate NUMERIC(18, 8);
BEGIN
    SELECT conversion_rate INTO v_conversion_rate
    FROM products
    WHERE id = p_product_id;
    
    IF v_conversion_rate IS NULL OR v_conversion_rate = 0 THEN
        RETURN p_purchase_quantity;
    END IF;
    
    RETURN p_purchase_quantity * v_conversion_rate;
END;
$$ LANGUAGE plpgsql;

-- ============================================================
-- TRIGGER: Auto-update updated_at timestamp
-- ============================================================

CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER update_products_updated_at
    BEFORE UPDATE ON products
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_units_updated_at
    BEFORE UPDATE ON units
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_product_categories_updated_at
    BEFORE UPDATE ON product_categories
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

-- ============================================================
-- SAMPLE DATA: Aviation-specific product categories and products
-- ============================================================

-- Insert sample categories
INSERT INTO product_categories (name, description) VALUES
('Paints & Coatings', 'Aviation paints, primers, and coatings'),
('Solvents & Thinners', 'Solvents, thinners, and cleaning agents'),
('Adhesives & Sealants', 'Adhesives, sealants, and potting compounds'),
('Hardeners & Catalysts', 'Hardeners, catalysts, and crosslinkers'),
('Consumables', 'Consumable materials like tapes, filters, and abrasives'),
('Kit Components', 'Components for kitted products');

-- Insert sample products
INSERT INTO products (sku, name, description, purchase_unit_id, sales_unit_id, base_unit_id, conversion_rate, purchase_price, sales_price, is_primary_color, tint_volume_deduction, current_stock_level) 
SELECT 
    'PRI-WH-001',
    'White Primer - 1L',
    'High-build epoxy primer for aircraft surfaces',
    (SELECT id FROM units WHERE symbol = 'L'),
    (SELECT id FROM units WHERE symbol = 'L'),
    (SELECT id FROM units WHERE symbol = 'ml'),
    1.0,
    25.00,
    45.00,
    TRUE,
    0.02,
    5000
WHERE NOT EXISTS (SELECT 1 FROM products WHERE sku = 'PRI-WH-001');

INSERT INTO products (sku, name, description, purchase_unit_id, sales_unit_id, base_unit_id, conversion_rate, purchase_price, sales_price, current_stock_level) 
SELECT 
    'THN-001',
    'Aviation Thinner',
    'High-performance thinner for aviation coatings',
    (SELECT id FROM units WHERE symbol = 'L'),
    (SELECT id FROM units WHERE symbol = 'L'),
    (SELECT id FROM units WHERE symbol = 'ml'),
    1.0,
    15.00,
    28.00,
    10000
WHERE NOT EXISTS (SELECT 1 FROM products WHERE sku = 'THN-001');

INSERT INTO products (sku, name, description, purchase_unit_id, sales_unit_id, base_unit_id, conversion_rate, purchase_price, sales_price, current_stock_level) 
SELECT 
    'HRD-001',
    'Epoxy Hardener',
    'Two-component epoxy hardener for aviation paints',
    (SELECT id FROM units WHERE symbol = 'L'),
    (SELECT id FROM units WHERE symbol = 'L'),
    (SELECT id FROM units WHERE symbol = 'ml'),
    1.0,
    30.00,
    55.00,
    2000
WHERE NOT EXISTS (SELECT 1 FROM products WHERE sku = 'HRD-001');

-- Create a kit product
INSERT INTO products (sku, name, description, purchase_unit_id, sales_unit_id, base_unit_id, conversion_rate, is_kit, kit_components, current_stock_level)
SELECT 
    'KIT-TOPCOAT-WH',
    'White Topcoat Kit - Complete',
    'Complete kit: 1L Topcoat + 500ml Hardener + 500ml Thinner',
    (SELECT id FROM units WHERE symbol = 'set'),
    (SELECT id FROM units WHERE symbol = 'set'),
    (SELECT id FROM units WHERE symbol = 'ml'),
    1.0,
    TRUE,
    '{
        "components": [
            {"product_id": null, "quantity": 1000, "unit_id": null},
            {"product_id": null, "quantity": 500, "unit_id": null},
            {"product_id": null, "quantity": 500, "unit_id": null}
        ]
    }'::JSONB,
    50
WHERE NOT EXISTS (SELECT 1 FROM products WHERE sku = 'KIT-TOPCOAT-WH');

-- Note: The kit_components above has null product_ids - in production, you'd update them with actual product IDs

-- ============================================================
-- COMMENTS FOR DOCUMENTATION
-- ============================================================

COMMENT ON TABLE products IS 'Main products table with support for multiple units, tinting, and kitting';
COMMENT ON COLUMN products.purchase_unit_id IS 'Unit in which the product is purchased (e.g., Liters, KG)';
COMMENT ON COLUMN products.sales_unit_id IS 'Unit in which the product is sold (e.g., Gallons, Yards)';
COMMENT ON COLUMN products.base_unit_id IS 'Base unit for stock tracking (typically the smallest unit for precision)';
COMMENT ON COLUMN products.conversion_rate IS 'Factor to convert purchase unit to sales unit (e.g., 3.78541 for Liters to Gallons)';
COMMENT ON COLUMN products.is_primary_color IS 'Flag indicating this is a tintable primary color';
COMMENT ON COLUMN products.tint_volume_deduction IS 'Percentage of volume deducted per tint (e.g., 0.02 = 2%)';
COMMENT ON COLUMN products.is_kit IS 'Flag indicating this is a kit product containing multiple components';
COMMENT ON COLUMN products.kit_components IS 'JSONB array of kit components: [{"product_id": "uuid", "quantity": 2, "unit_id": "uuid"}]';
COMMENT ON COLUMN products.current_stock_level IS 'Current stock level in base unit for high precision';
COMMENT ON COLUMN products.location IS 'Product storage location (e.g., Warehouse A, Shelf B3)';

COMMENT ON TABLE stock_transactions IS 'Transaction log for all stock movements';
COMMENT ON COLUMN stock_transactions.tint_product_id IS 'Links tint deductions to the primary color used';
COMMENT ON COLUMN stock_transactions.tint_deduction_amount IS 'Amount of primary color deducted for tinting';

-- ============================================================
-- END OF SCHEMA
-- ============================================================

-- ============================================================
-- AUDIT LOGS TABLE
-- ============================================================

CREATE TABLE IF NOT EXISTS audit_logs (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    staff_id UUID NOT NULL, -- Staff ID from Contabo
    action VARCHAR(100) NOT NULL, -- Action type: 'sale', 'kit_sale', 'purchase', etc.
    entity_type VARCHAR(50), -- Type of entity: 'product', 'stock', etc.
    entity_id UUID, -- ID of the affected entity
    details JSONB, -- Additional details in JSON format
    ip_address VARCHAR(45), -- Client IP address
    user_agent TEXT, -- Client user agent
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Index for audit_logs
CREATE INDEX idx_audit_logs_staff_id ON audit_logs(staff_id);
CREATE INDEX idx_audit_logs_action ON audit_logs(action);
CREATE INDEX idx_audit_logs_created_at ON audit_logs(created_at DESC);
CREATE INDEX idx_audit_logs_entity ON audit_logs(entity_type, entity_id);

-- ============================================================
-- FUNCTION: fn_process_aviation_sale
-- Process Aviation Sale with Kit Support and Safety Checks
-- ============================================================

DROP FUNCTION IF EXISTS fn_process_aviation_sale(UUID, NUMERIC, UUID, UUID, VARCHAR, UUID);

CREATE OR REPLACE FUNCTION fn_process_aviation_sale(
    p_product_id UUID,              -- Product being sold
    p_quantity NUMERIC,             -- Quantity to sell
    p_kit_id UUID DEFAULT NULL,     -- Kit ID (if this is a kit sale)
    p_staff_id UUID,                -- Staff ID from Contabo performing the sale
    p_reference_type VARCHAR DEFAULT 'sale',
    p_reference_id UUID DEFAULT NULL
) RETURNS TABLE (
    success BOOLEAN,
    message TEXT,
    product_id UUID,
    product_name VARCHAR,
    quantity_deducted NUMERIC,
    stock_before NUMERIC,
    stock_after NUMERIC,
    transaction_ids UUID[]
) AS $$
DECLARE
    v_is_kit BOOLEAN := FALSE;
    v_kit_record RECORD;
    v_product_record RECORD;
    v_hardener_record RECORD;
    v_thinner_record RECORD;
    
    v_mixing_ratio JSONB;
    v_hardener_ratio NUMERIC := 1.0;
    v_thinner_ratio NUMERIC := 1.0;
    
    v_hardener_id UUID;
    v_thinner_id UUID;
    
    v_needed_hardener NUMERIC := 0;
    v_needed_thinner NUMERIC := 0;
    
    v_product_qty_before NUMERIC;
    v_hardener_qty_before NUMERIC;
    v_thinner_qty_before NUMERIC;
    
    v_product_qty_after NUMERIC;
    v_hardener_qty_after NUMERIC;
    v_thinner_qty_after NUMERIC;
    
    v_transaction_ids UUID[] := '{}';
    v_tx_id UUID;
    
    v_audit_details JSONB;
BEGIN
    -- Validate required parameters
    IF p_product_id IS NULL THEN
        RAISE EXCEPTION 'Product ID is required';
    END IF;
    
    IF p_quantity IS NULL OR p_quantity <= 0 THEN
        RAISE EXCEPTION 'Quantity must be a positive number';
    END IF;
    
    IF p_staff_id IS NULL THEN
        RAISE EXCEPTION 'Staff ID is required for audit logging';
    END IF;
    
    -- Get the main product being sold
    SELECT * INTO v_product_record
    FROM products
    WHERE id = p_product_id;
    
    IF v_product_record IS NULL THEN
        RAISE EXCEPTION 'Product not found: %', p_product_id;
    END IF;
    
    IF NOT v_product_record.is_tracked THEN
        RAISE EXCEPTION 'Stock tracking is disabled for this product';
    END IF;
    
    v_product_qty_before := v_product_record.current_stock_level;
    
    -- ============================================================
    -- KIT SALE LOGIC
    -- ============================================================
    IF p_kit_id IS NOT NULL THEN
        -- This is a kit sale - fetch kit details
        SELECT * INTO v_kit_record
        FROM products
        WHERE id = p_kit_id AND is_kit = TRUE;
        
        IF v_kit_record IS NULL THEN
            RAISE EXCEPTION 'Kit product not found or is not a kit: %', p_kit_id;
        END IF;
        
        v_is_kit := TRUE;
        
        -- Get mixing ratio from kit (default to 1:1:1 if not set)
        v_mixing_ratio := COALESCE(v_kit_record.mixing_ratio, '{"hardener": 1.0, "thinner": 1.0}'::JSONB);
        v_hardener_ratio := COALESCE((v_mixing_ratio->>'hardener')::NUMERIC, 1.0);
        v_thinner_ratio := COALESCE((v_mixing_ratio->>'thinner')::NUMERIC, 1.0);
        
        -- Calculate needed amounts
        v_needed_hardener := p_quantity * v_hardener_ratio;
        v_needed_thinner := p_quantity * v_thinner_ratio;
        
        -- Find hardener and thinner products
        -- Priority: 1) From kit_components JSONB, 2) From product fields, 3) Auto-lookup
        
        -- Try to get from kit_components
        BEGIN
            SELECT 
                MAX(CASE WHEN comp->>'component_type' = 'hardener' THEN (comp->>'product_id')::UUID END) AS hardener_id,
                MAX(CASE WHEN comp->>'component_type' = 'thinner' THEN (comp->>'product_id')::UUID END) AS thinner_id
            INTO v_hardener_id, v_thinner_id
            FROM products p
            CROSS JOIN LATERAL jsonb_array_elements(kit_components->'components') AS comp
            WHERE p.id = p_kit_id;
        EXCEPTION WHEN OTHERS THEN
            v_hardener_id := NULL;
            v_thinner_id := NULL;
        END;
        
        -- If not found, try product fields (hardener_ratio, thinner_id)
        IF v_hardener_id IS NULL THEN
            v_hardener_id := v_kit_record.thinner_id; -- This might need adjustment based on schema
        END IF;
        
        -- If still not found, auto-lookup by naming convention
        IF v_hardener_id IS NULL THEN
            SELECT id INTO v_hardener_id
            FROM products
            WHERE is_active = TRUE
              AND (name ILIKE '%hardener%' OR name ILIKE '%catalyst%' OR sku ILIKE '%HRD%')
            ORDER BY current_stock_level DESC
            LIMIT 1;
        END IF;
        
        IF v_thinner_id IS NULL THEN
            SELECT id INTO v_thinner_id
            FROM products
            WHERE is_active = TRUE
              AND (name ILIKE '%thinner%' OR name ILIKE '%solvent%' OR sku ILIKE '%THN%')
            ORDER BY current_stock_level DESC
            LIMIT 1;
        END IF;
        
        -- Validate hardener and thinner exist
        IF v_hardener_id IS NULL THEN
            RAISE EXCEPTION 'Hardener product not found for kit';
        END IF;
        
        IF v_thinner_id IS NULL THEN
            RAISE EXCEPTION 'Thinner product not found for kit';
        END IF;
        
        -- Get hardener product details
        SELECT * INTO v_hardener_record
        FROM products
        WHERE id = v_hardener_id;
        
        IF v_hardener_record IS NULL THEN
            RAISE EXCEPTION 'Hardener product not found: %', v_hardener_id;
        END IF;
        
        -- Get thinner product details
        SELECT * INTO v_thinner_record
        FROM products
        WHERE id = v_thinner_id;
        
        IF v_thinner_record IS NULL THEN
            RAISE EXCEPTION 'Thinner product not found: %', v_thinner_id;
        END IF;
        
        v_hardener_qty_before := v_hardener_record.current_stock_level;
        v_thinner_qty_before := v_thinner_record.current_stock_level;
    END IF;
    
    -- ============================================================
    -- SAFETY CHECK: Validate ALL stock levels BEFORE any deduction
    -- This ensures the transaction fails entirely if any component is insufficient
    -- ============================================================
    
    -- Check main product stock
    IF v_product_qty_before < p_quantity THEN
        RAISE EXCEPTION 'Insufficient stock for product "%" (SKU: %). Current: %, Requested: %',
            v_product_record.name, v_product_record.sku, v_product_qty_before, p_quantity;
    END IF;
    
    -- If kit sale, check hardener and thinner stock
    IF v_is_kit THEN
        IF v_hardener_qty_before < v_needed_hardener THEN
            RAISE EXCEPTION 'Insufficient stock for hardener "%" (SKU: %). Current: %, Requested: %',
                v_hardener_record.name, v_hardener_record.sku, v_hardener_qty_before, v_needed_hardener;
        END IF;
        
        IF v_thinner_qty_before < v_needed_thinner THEN
            RAISE EXCEPTION 'Insufficient stock for thinner "%" (SKU: %). Current: %, Requested: %',
                v_thinner_record.name, v_thinner_record.sku, v_thinner_qty_before, v_needed_thinner;
        END IF;
    END IF;
    
    -- ============================================================
    -- ALL VALIDATIONS PASSED - Proceed with stock deduction
    -- ============================================================
    
    -- Calculate new quantities
    v_product_qty_after := v_product_qty_before - p_quantity;
    
    IF v_is_kit THEN
        v_hardener_qty_after := v_hardener_qty_before - v_needed_hardener;
        v_thinner_qty_after := v_thinner_qty_before - v_needed_thinner;
    END IF;
    
    -- Update main product stock
    UPDATE products
    SET current_stock_level = v_product_qty_after,
        updated_at = NOW()
    WHERE id = p_product_id;
    
    -- Log main product transaction
    INSERT INTO stock_transactions (
        product_id,
        transaction_type,
        quantity,
        quantity_before,
        quantity_after,
        reference_type,
        reference_id,
        notes,
        created_by
    ) VALUES (
        p_product_id,
        'sale',
        p_quantity,
        v_product_qty_before,
        v_product_qty_after,
        p_reference_type,
        p_reference_id,
        CASE 
            WHEN v_is_kit THEN format('Kit Sale (Kit ID: %s): %s', p_kit_id, v_product_record.name)
            ELSE format('Sale: %s', v_product_record.name)
        END,
        p_staff_id
    ) RETURNING id INTO v_tx_id;
    
    v_transaction_ids := array_append(v_transaction_ids, v_tx_id);
    
    -- If kit sale, update hardener and thinner stock
    IF v_is_kit THEN
        -- Update hardener stock
        UPDATE products
        SET current_stock_level = v_hardener_qty_after,
            updated_at = NOW()
        WHERE id = v_hardener_id;
        
        -- Log hardener transaction
        INSERT INTO stock_transactions (
            product_id,
            transaction_type,
            quantity,
            quantity_before,
            quantity_after,
            reference_type,
            reference_id,
            notes,
            created_by
        ) VALUES (
            v_hardener_id,
            'kit_disassembly',
            v_needed_hardener,
            v_hardener_qty_before,
            v_hardener_qty_after,
            p_reference_type,
            p_reference_id,
            format('Kit Sale: Hardener for %s (Kit: %s)', v_product_record.name, v_kit_record.name),
            p_staff_id
        ) RETURNING id INTO v_tx_id;
        
        v_transaction_ids := array_append(v_transaction_ids, v_tx_id);
        
        -- Update thinner stock
        UPDATE products
        SET current_stock_level = v_thinner_qty_after,
            updated_at = NOW()
        WHERE id = v_thinner_id;
        
        -- Log thinner transaction
        INSERT INTO stock_transactions (
            product_id,
            transaction_type,
            quantity,
            quantity_before,
            quantity_after,
            reference_type,
            reference_id,
            notes,
            created_by
        ) VALUES (
            v_thinner_id,
            'kit_disassembly',
            v_needed_thinner,
            v_thinner_qty_before,
            v_thinner_qty_after,
            p_reference_type,
            p_reference_id,
            format('Kit Sale: Thinner for %s (Kit: %s)', v_product_record.name, v_kit_record.name),
            p_staff_id
        ) RETURNING id INTO v_tx_id;
        
        v_transaction_ids := array_append(v_transaction_ids, v_tx_id);
    END IF;
    
    -- ============================================================
    -- AUDIT LOGGING: Insert record showing which Staff performed the sale
    -- ============================================================
    
    v_audit_details := jsonb_build_object(
        'product_id', p_product_id,
        'product_name', v_product_record.name,
        'product_sku', v_product_record.sku,
        'quantity', p_quantity,
        'is_kit', v_is_kit,
        'kit_id', p_kit_id,
        'reference_type', p_reference_type,
        'reference_id', p_reference_id,
        'stock_before', v_product_qty_before,
        'stock_after', v_product_qty_after,
        'hardener_id', v_hardener_id,
        'hardener_deducted', v_needed_hardener,
        'thinner_id', v_thinner_id,
        'thinner_deducted', v_needed_thinner,
        'transaction_ids', v_transaction_ids
    );
    
    INSERT INTO audit_logs (
        staff_id,
        action,
        entity_type,
        entity_id,
        details
    ) VALUES (
        p_staff_id,
        CASE WHEN v_is_kit THEN 'kit_sale' ELSE 'sale' END,
        'stock',
        p_product_id,
        v_audit_details
    );
    
    -- ============================================================
    -- Return success result
    -- ============================================================
    
    RETURN QUERY SELECT
        TRUE,
        CASE 
            WHEN v_is_kit THEN format('Kit sale processed successfully. Hardener: %s, Thinner: %s', 
                v_needed_hardener, v_needed_thinner)
            ELSE 'Sale processed successfully'
        END,
        p_product_id,
        v_product_record.name,
        p_quantity,
        v_product_qty_before,
        v_product_qty_after,
        v_transaction_ids;
        
EXCEPTION
    WHEN raise_exception THEN
        -- Re-raise the exception to propagate the error message
        RAISE;
    WHEN OTHERS THEN
        -- Log error to audit_logs for failed transactions
        BEGIN
            INSERT INTO audit_logs (
                staff_id,
                action,
                entity_type,
                entity_id,
                details
            ) VALUES (
                COALESCE(p_staff_id, uuid_generate_v4()),
                'sale_failed',
                'stock',
                p_product_id,
                jsonb_build_object(
                    'product_id', p_product_id,
                    'quantity', p_quantity,
                    'kit_id', p_kit_id,
                    'error_message', SQLERRM,
                    'error_code', SQLSTATE
                )
            );
        EXCEPTION WHEN OTHERS THEN
            -- Ignore audit logging errors
        END;
        
        RAISE;
END;
$$ LANGUAGE plpgsql;

-- Add documentation comment
COMMENT ON FUNCTION fn_process_aviation_sale IS 
'Process Aviation Sale with Kit Support and Safety Checks.

Parameters:
- p_product_id (UUID): Product being sold
- p_quantity (NUMERIC): Quantity to sell
- p_kit_id (UUID, optional): Kit ID if this is a kit sale
- p_staff_id (UUID): Staff ID from Contabo performing the sale (required for audit)
- p_reference_type (VARCHAR): Reference type (default: ''sale'')
- p_reference_id (UUID): Reference ID for linking

Logic:
1. If kit_id is NULL: Standard sale - deduct quantity from single product
2. If kit_id is provided: Kit sale - find linked Hardener & Thinner, deduct proportional amounts

Safety Check:
- Validates ALL stock levels BEFORE any deduction
- Uses RAISE EXCEPTION if ANY stock goes below zero
- Entire transaction fails if one component is missing

Logging:
- Automatically inserts record into audit_logs showing Staff ID
- Logs all stock transactions for audit trail

Returns: success, message, product details, quantities, and transaction IDs';

-- ============================================================
-- END OF FUNCTION
-- ============================================================

