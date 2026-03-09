-- ============================================================
-- FUNCTION: process_kit_sale
-- Process Paint Kit Sale with Stock Validation
-- ============================================================

-- Drop function if exists for fresh creation
DROP FUNCTION IF EXISTS process_kit_sale(UUID, FLOAT, FLOAT, FLOAT);
DROP FUNCTION IF EXISTS process_kit_sale(UUID, FLOAT, FLOAT, FLOAT, UUID, UUID);

CREATE OR REPLACE FUNCTION process_kit_sale(
    p_primary_paint_id UUID,
    p_requested_primary_qty FLOAT,
    p_ratio_hardener FLOAT,
    p_ratio_thinner FLOAT,
    p_hardener_id UUID DEFAULT NULL,
    p_thinner_id UUID DEFAULT NULL
) RETURNS TABLE (
    success BOOLEAN,
    message TEXT,
    primary_paint_id UUID,
    hardener_id UUID,
    thinner_id UUID,
    primary_paint_deducted FLOAT,
    hardener_deducted FLOAT,
    thinner_deducted FLOAT,
    transaction_ids UUID[]
) AS $$
DECLARE
    v_primary_record RECORD;
    v_hardener_record RECORD;
    v_thinner_record RECORD;
    
    v_needed_hardener FLOAT;
    v_needed_thinner FLOAT;
    
    v_primary_quantity_before FLOAT;
    v_hardener_quantity_before FLOAT;
    v_thinner_quantity_before FLOAT;
    
    v_primary_quantity_after FLOAT;
    v_hardener_quantity_after FLOAT;
    v_thinner_quantity_after FLOAT;
    
    v_transaction_ids UUID[] := '{}';
    v_tx_id UUID;
    
    v_hardener_product_id UUID;
    v_thinner_product_id UUID;
BEGIN
    -- Validate inputs
    IF p_primary_paint_id IS NULL THEN
        RETURN QUERY SELECT FALSE, 'Primary paint ID is required', NULL, NULL, NULL, NULL, NULL, NULL, NULL;
    END IF;
    
    IF p_requested_primary_qty IS NULL OR p_requested_primary_qty <= 0 THEN
        RETURN QUERY SELECT FALSE, 'Requested primary quantity must be positive', NULL, NULL, NULL, NULL, NULL, NULL, NULL;
    END IF;
    
    IF p_ratio_hardener IS NULL OR p_ratio_hardener < 0 THEN
        RETURN QUERY SELECT FALSE, 'Ratio hardener must be non-negative', NULL, NULL, NULL, NULL, NULL, NULL, NULL;
    END IF;
    
    IF p_ratio_thinner IS NULL OR p_ratio_thinner < 0 THEN
        RETURN QUERY SELECT FALSE, 'Ratio thinner must be non-negative', NULL, NULL, NULL, NULL, NULL, NULL, NULL;
    END IF;
    
    -- Get the primary paint product
    SELECT * INTO v_primary_record 
    FROM products 
    WHERE id = p_primary_paint_id;
    
    IF v_primary_record IS NULL THEN
        RETURN QUERY SELECT FALSE, 'Primary paint product not found', NULL, NULL, NULL, NULL, NULL, NULL, NULL;
    END IF;
    
    -- Calculate needed amounts
    v_needed_hardener := p_requested_primary_qty * p_ratio_hardener;
    v_needed_thinner := p_requested_primary_qty * p_ratio_thinner;
    
    -- Determine hardener and thinner product IDs
    -- Priority: 1) Explicitly passed parameters, 2) Look up from kit_components, 3) Look up by naming convention
    v_hardener_product_id := p_hardener_id;
    v_thinner_product_id := p_thinner_id;
    
    -- If not provided, try to find from kit_components
    IF v_hardener_product_id IS NULL OR v_thinner_product_id IS NULL THEN
        BEGIN
            SELECT 
                MAX(CASE WHEN component->>'component_type' = 'hardener' THEN (component->>'product_id')::UUID END) AS hardener_id,
                MAX(CASE WHEN component->>'component_type' = 'thinner' THEN (component->>'product_id')::UUID END) AS thinner_id
            INTO v_hardener_product_id, v_thinner_product_id
            FROM products p
            CROSS JOIN LATERAL jsonb_array_elements(kit_components->'components') AS component
            WHERE p.id = p_primary_paint_id;
        END;
    END IF;
    
    -- If still not found, try naming convention lookup
    IF v_hardener_product_id IS NULL THEN
        SELECT id INTO v_hardener_product_id
        FROM products
        WHERE is_active = TRUE
          AND (name ILIKE '%hardener%' OR name ILIKE '%catalyst%' OR sku ILIKE '%HRD%')
        ORDER BY current_stock_level DESC
        LIMIT 1;
    END IF;
    
    IF v_thinner_product_id IS NULL THEN
        SELECT id INTO v_thinner_product_id
        FROM products
        WHERE is_active = TRUE
          AND (name ILIKE '%thinner%' OR name ILIKE '%solvent%' OR sku ILIKE '%THN%')
        ORDER BY current_stock_level DESC
        LIMIT 1;
    END IF;
    
    -- Validate hardener and thinner products exist
    IF v_hardener_product_id IS NULL THEN
        RETURN QUERY SELECT FALSE, 'Hardener product not found or not configured', NULL, NULL, NULL, NULL, NULL, NULL, NULL;
    END IF;
    
    IF v_thinner_product_id IS NULL THEN
        RETURN QUERY SELECT FALSE, 'Thinner product not found or not configured', NULL, NULL, NULL, NULL, NULL, NULL, NULL;
    END IF;
    
    -- Get hardener product details
    SELECT * INTO v_hardener_record 
    FROM products 
    WHERE id = v_hardener_product_id;
    
    IF v_hardener_record IS NULL THEN
        RETURN QUERY SELECT FALSE, 'Hardener product not found', NULL, NULL, NULL, NULL, NULL, NULL, NULL;
    END IF;
    
    -- Get thinner product details
    SELECT * INTO v_thinner_record 
    FROM products 
    WHERE id = v_thinner_product_id;
    
    IF v_thinner_record IS NULL THEN
        RETURN QUERY SELECT FALSE, 'Thinner product not found', NULL, NULL, NULL, NULL, NULL, NULL, NULL;
    END IF;
    
    -- Store quantities before
    v_primary_quantity_before := v_primary_record.current_stock_level;
    v_hardener_quantity_before := v_hardener_record.current_stock_level;
    v_thinner_quantity_before := v_thinner_record.current_stock_level;
    
    -- VALIDATION: Check stock for ALL three items
    -- If ANY item has insufficient stock, ROLLBACK and return error
    IF v_primary_quantity_before < p_requested_primary_qty THEN
        RAISE EXCEPTION 'Insufficient Stock for Kit Components';
    END IF;
    
    IF v_hardener_quantity_before < v_needed_hardener THEN
        RAISE EXCEPTION 'Insufficient Stock for Kit Components';
    END IF;
    
    IF v_thinner_quantity_before < v_needed_thinner THEN
        RAISE EXCEPTION 'Insufficient Stock for Kit Components';
    END IF;
    
    -- All validations passed - proceed with deductions
    
    -- Calculate quantities after
    v_primary_quantity_after := v_primary_quantity_before - p_requested_primary_qty;
    v_hardener_quantity_after := v_hardener_quantity_before - v_needed_hardener;
    v_thinner_quantity_after := v_thinner_quantity_before - v_needed_thinner;
    
    -- Update primary paint stock
    UPDATE products 
    SET current_stock_level = v_primary_quantity_after,
        updated_at = NOW()
    WHERE id = p_primary_paint_id;
    
    -- Update hardener stock
    UPDATE products 
    SET current_stock_level = v_hardener_quantity_after,
        updated_at = NOW()
    WHERE id = v_hardener_product_id;
    
    -- Update thinner stock
    UPDATE products 
    SET current_stock_level = v_thinner_quantity_after,
        updated_at = NOW()
    WHERE id = v_thinner_product_id;
    
    -- Log stock transaction for primary paint (sale)
    INSERT INTO stock_transactions (
        product_id,
        transaction_type,
        quantity,
        quantity_before,
        quantity_after,
        reference_type,
        notes,
        created_at
    ) VALUES (
        p_primary_paint_id,
        'sale',
        p_requested_primary_qty,
        v_primary_quantity_before,
        v_primary_quantity_after,
        'kit_sale',
        format('Kit Sale: Primary paint %s', v_primary_record.name),
        NOW()
    ) RETURNING id INTO v_tx_id;
    
    v_transaction_ids := array_append(v_transaction_ids, v_tx_id);
    
    -- Log stock transaction for hardener (kit_disassembly)
    INSERT INTO stock_transactions (
        product_id,
        transaction_type,
        quantity,
        quantity_before,
        quantity_after,
        reference_type,
        notes,
        created_at
    ) VALUES (
        v_hardener_product_id,
        'kit_disassembly',
        v_needed_hardener,
        v_hardener_quantity_before,
        v_hardener_quantity_after,
        'kit_sale',
        format('Kit Sale: Hardener for paint %s', v_primary_record.name),
        NOW()
    ) RETURNING id INTO v_tx_id;
    
    v_transaction_ids := array_append(v_transaction_ids, v_tx_id);
    
    -- Log stock transaction for thinner (kit_disassembly)
    INSERT INTO stock_transactions (
        product_id,
        transaction_type,
        quantity,
        quantity_before,
        quantity_after,
        reference_type,
        notes,
        created_at
    ) VALUES (
        v_thinner_product_id,
        'kit_disassembly',
        v_needed_thinner,
        v_thinner_quantity_before,
        v_thinner_quantity_after,
        'kit_sale',
        format('Kit Sale: Thinner for paint %s', v_primary_record.name),
        NOW()
    ) RETURNING id INTO v_tx_id;
    
    v_transaction_ids := array_append(v_transaction_ids, v_tx_id);
    
    -- Return success
    RETURN QUERY SELECT 
        TRUE,
        'Kit Sale processed successfully',
        p_primary_paint_id,
        v_hardener_product_id,
        v_thinner_product_id,
        p_requested_primary_qty,
        v_needed_hardener,
        v_needed_thinner,
        v_transaction_ids;
    
EXCEPTION
    WHEN raise_exception THEN
        -- Re-raise the exception to propagate the error message
        RAISE;
    WHEN OTHERS THEN
        -- Rollback and return error
        RAISE EXCEPTION 'Insufficient Stock for Kit Components';
END;
$$ LANGUAGE plpgsql;

-- Add comment for documentation
COMMENT ON FUNCTION process_kit_sale IS 
'Process a paint kit sale with stock validation.

Inputs:
- p_primary_paint_id (UUID): ID of the primary paint/product
- p_requested_primary_qty (FLOAT): Quantity of primary paint requested
- p_ratio_hardener (FLOAT): Ratio of hardener to primary (e.g., 0.5 means 50% of primary qty)
- p_ratio_thinner (FLOAT): Ratio of thinner to primary (e.g., 0.3 means 30% of primary qty)
- p_hardener_id (UUID, optional): ID of hardener product (auto-looked up if not provided)
- p_thinner_id (UUID, optional): ID of thinner product (auto-looked up if not provided)

Logic:
1. Calculates needed_hardener = requested_primary_qty * ratio_hardener
2. Calculates needed_thinner = requested_primary_qty * ratio_thinner

Validation:
- Checks if current_stock for ANY of the three items is less than the needed amount
- If insufficient, ROLLBACK and returns error: ''Insufficient Stock for Kit Components''

Execution:
- If stock is available, UPDATE products table by subtracting calculated amounts from all three rows
- Log each transaction in stock_transactions table

Returns: success, message, product IDs, deducted quantities, and transaction IDs';

