/**
 * Aviation ERP - Staff Site Sale Input Handler
 * Handles real-time calculations for Paint Kits and Carpets with stock validation
 * 
 * Features:
 * - Paint Kits: Auto-calculate hardener and thinner requirements based on mixing ratio
 * - Carpets: Convert yards to meters with 5% aviation wastage
 * - Stock Validation: Compare calculated totals against available stock
 * - UI Updates: Show previews and disable confirm button when insufficient stock
 * 
 * @version 1.0.0
 */

// =============================================================================
// CONFIGURATION
// =============================================================================

const SALE_INPUT_CONFIG = {
    // Conversion constants
    YARD_TO_METER: 0.9144,
    INCH_TO_METER: 0.0254,
    
    // Aviation wastage factor (5%)
    WASTAGE_FACTOR: 0.05,
    
    // API endpoints
    API_BASE_URL: '/api',
    
    // DOM element IDs (can be customized per implementation)
    DEFAULT_ELEMENT_IDS: {
        quantityInput: 'quantity',
        productSelect: 'product',
        categorySelect: 'category',
        unitSelect: 'unit',
        hardenerRequired: 'hardener_required',
        thinnerRequired: 'thinner_required',
        metersToDeduct: 'meters_to_deduct',
        currentStock: 'current_stock',
        confirmButton: 'confirm_sale_btn',
        stockWarning: 'stock_warning',
        previewContainer: 'preview_container'
    }
};

// =============================================================================
// HELPER FUNCTIONS
// =============================================================================

/**
 * Convert yards to meters
 * @param {number} yards - Quantity in yards
 * @returns {number} Quantity in meters
 */
function yardsToMeters(yards) {
    return yards * SALE_INPUT_CONFIG.YARD_TO_METER;
}

/**
 * Convert inches to meters
 * @param {number} inches - Quantity in inches
 * @returns {number} Quantity in meters
 */
function inchesToMeters(inches) {
    return inches * SALE_INPUT_CONFIG.INCH_TO_METER;
}

/**
 * Calculate total meters with 5% aviation wastage
 * @param {number} meters - Base quantity in meters
 * @returns {number} Total meters including wastage
 */
function calculateWithWastage(meters) {
    return meters * (1 + SALE_INPUT_CONFIG.WASTAGE_FACTOR);
}

/**
 * Round to 2 decimal places
 * @param {number} value - Value to round
 * @returns {number} Rounded value
 */
function roundToTwo(value) {
    return Math.round(value * 100) / 100;
}

/**
 * Check if category is Carpet
 * @param {string} categoryName - Category name
 * @returns {boolean} True if Carpet
 */
function isCarpetCategory(categoryName) {
    if (!categoryName) return false;
    return categoryName.toLowerCase().includes('carpet');
}

/**
 * Check if unit is Yards
 * @param {string} unit - Unit string
 * @returns {boolean} True if Yards
 */
function isYardsUnit(unit) {
    if (!unit) return false;
    const normalized = unit.toLowerCase().trim();
    return normalized === 'yards' || normalized === 'yd' || normalized === 'yard';
}

// =============================================================================
// MAIN HANDLER FUNCTION
// =============================================================================

/**
 * Handle Sale Input - Main function for Staff Site
 * 
 * This function should be called when:
 * 1. A product is selected from the dropdown
 * 2. The quantity input changes
 * 3. The unit selection changes
 * 
 * @param {Object} options - Configuration options
 * @param {Object} options.product - Selected product data from API
 * @param {number} options.quantity - Current quantity value
 * @param {string} options.unitSelected - Selected unit (yards, inches, lts, etc.)
 * @param {Object} options.elements - DOM element references
 * @param {Object} options.apiClient - Optional API client for fetching product data
 * @returns {Object} Calculation results
 * 
 * @example
 * // Basic usage with DOM elements
 * const result = handleSaleInput({
 *     product: selectedProduct,
 *     quantity: parseFloat(quantityInput.value),
 *     unitSelected: unitSelect.value,
 *     elements: {
 *         quantityInput: document.getElementById('quantity'),
 *         hardenerRequired: document.getElementById('hardener_required'),
 *         thinnerRequired: document.getElementById('thinner_required'),
 *         metersToDeduct: document.getElementById('meters_to_deduct'),
 *         currentStock: document.getElementById('current_stock'),
 *         confirmButton: document.getElementById('confirm_sale_btn')
 *     }
 * });
 */
function handleSaleInput(options) {
    // Destructure options with defaults
    const {
        product = null,
        quantity = 0,
        unitSelected = '',
        elements = {},
        apiClient = null
    } = options;

    // Initialize result object
    const result = {
        success: true,
        isKit: false,
        isCarpet: false,
        hasInsufficientStock: false,
        quantity: quantity,
        unitSelected: unitSelected,
        hardenerRequired: 0,
        thinnerRequired: 0,
        metersToDeduct: 0,
        currentStock: 0,
        calculatedTotal: 0,
        message: ''
    };

    // Validate required inputs
    if (!product) {
        result.message = 'No product selected';
        return result;
    }

    if (!quantity || quantity <= 0) {
        result.message = 'Please enter a valid quantity';
        clearPreviewFields(elements);
        enableConfirmButton(elements);
        return result;
    }

    // Get product properties
    const isKit = product.is_kit === true || product.is_kit === 'true';
    const categoryName = product.category_name || product.category || '';
    const isCarpet = isCarpetCategory(categoryName);
    const currentStock = parseFloat(product.current_stock_level) || parseFloat(product.current_stock) || 0;
    
    result.isKit = isKit;
    result.isCarpet = isCarpet;
    result.currentStock = currentStock;

    // =============================================================================
    // PAINT KIT LOGIC
    // =============================================================================
    
    if (isKit) {
        // Get mixing ratio from product (default to 1:1 if not set)
        const mixingRatio = product.mixing_ratio || { hardener: 1.0, thinner: 1.0 };
        
        // Handle case where mixing_ratio might be a string
        let hardenerRatio = 1.0;
        let thinnerRatio = 1.0;
        
        if (typeof mixingRatio === 'string') {
            try {
                const parsed = JSON.parse(mixingRatio);
                hardenerRatio = parseFloat(parsed.hardener) || 1.0;
                thinnerRatio = parseFloat(parsed.thinner) || 1.0;
            } catch (e) {
                console.warn('Failed to parse mixing_ratio:', e);
            }
        } else if (typeof mixingRatio === 'object') {
            hardenerRatio = parseFloat(mixingRatio.hardener) || 1.0;
            thinnerRatio = parseFloat(mixingRatio.thinner) || 1.0;
        }
        
        // Also check for hardener_ratio field (direct field)
        if (product.hardener_ratio !== undefined && product.hardener_ratio !== null) {
            hardenerRatio = parseFloat(product.hardener_ratio) || 1.0;
        }
        
        // Calculate requirements
        result.hardenerRequired = roundToTwo(quantity * hardenerRatio);
        result.thinnerRequired = roundToTwo(quantity * thinnerRatio);
        
        // Total for kit includes all components
        // For kit: primary (quantity) + hardener + thinner
        result.calculatedTotal = quantity + result.hardenerRequired + result.thinnerRequired;
        
        // Update read-only fields for hardener and thinner
        updateKitFields(elements, result);
        
        // Clear carpet-specific fields
        clearCarpetFields(elements);
        
        result.message = `Kit selected: ${quantity} kit(s) = ${result.hardenerRequired}L hardener + ${result.thinnerRequired}L thinner`;
    }

    // =============================================================================
    // CARPET LOGIC
    // =============================================================================
    
    else if (isCarpet && isYardsUnit(unitSelected)) {
        // Convert yards to meters
        const metersBase = yardsToMeters(quantity);
        
        // Calculate with 5% wastage
        const metersWithWastage = calculateWithWastage(metersBase);
        
        result.metersToDeduct = roundToTwo(metersWithWastage);
        result.calculatedTotal = result.metersToDeduct;
        
        // Update carpet preview field
        updateCarpetFields(elements, result, quantity);
        
        // Clear kit-specific fields
        clearKitFields(elements);
        
        result.message = `${quantity} yards = ${metersBase.toFixed(3)}m + 5% wastage = ${result.metersToDeduct}m to deduct`;
    }
    
    // =============================================================================
    // REGULAR PRODUCT (NON-KIT, NON-CARPET)
    // =============================================================================
    
    else {
        // For regular products, just use the quantity as-is
        result.calculatedTotal = quantity;
        
        // Clear both kit and carpet fields
        clearKitFields(elements);
        clearCarpetFields(elements);
        
        result.message = `Regular product: ${quantity} units`;
    }

    // =============================================================================
    // STOCK VALIDATION
    // =============================================================================
    
    // Check if calculated total exceeds current stock
    if (result.calculatedTotal > currentStock) {
        result.hasInsufficientStock = true;
        result.message = `WARNING: Insufficient stock! Required: ${result.calculatedTotal}, Available: ${currentStock}`;
        
        // Update UI to show error state
        updateStockWarning(elements, result, true);
        disableConfirmButton(elements);
    } else {
        result.hasInsufficientStock = false;
        
        // Update UI to show normal state
        updateStockWarning(elements, result, false);
        enableConfirmButton(elements);
    }

    return result;
}

// =============================================================================
// UI UPDATE FUNCTIONS
// =============================================================================

/**
 * Update kit-related read-only fields
 * @param {Object} elements - DOM elements
 * @param {Object} result - Calculation result
 */
function updateKitFields(elements, result) {
    // Update hardener_required field
    if (elements.hardenerRequired) {
        const field = typeof elements.hardenerRequired === 'string' 
            ? document.getElementById(elements.hardenerRequired)
            : elements.hardenerRequired;
        
        if (field) {
            field.value = result.hardenerRequired;
            field.readOnly = true;
            field.classList.remove('insufficient-stock');
        }
    }
    
    // Update thinner_required field
    if (elements.thinnerRequired) {
        const field = typeof elements.thinnerRequired === 'string'
            ? document.getElementById(elements.thinnerRequired)
            : elements.thinnerRequired;
        
        if (field) {
            field.value = result.thinnerRequired;
            field.readOnly = true;
            field.classList.remove('insufficient-stock');
        }
    }
}

/**
 * Update carpet-related preview field
 * @param {Object} elements - DOM elements
 * @param {Object} result - Calculation result
 * @param {number} originalQuantity - Original yards input
 */
function updateCarpetFields(elements, result, originalQuantity) {
    // Update meters_to_deduct preview
    if (elements.metersToDeduct) {
        const field = typeof elements.metersToDeduct === 'string'
            ? document.getElementById(elements.metersToDeduct)
            : elements.metersToDeduct;
        
        if (field) {
            field.value = result.metersToDeduct;
            field.classList.remove('insufficient-stock');
            
            // Update with detailed preview text
            const wastageAmount = roundToTwo(result.metersToDeduct - (originalQuantity * SALE_INPUT_CONFIG.YARD_TO_METER));
            field.placeholder = `${originalQuantity} yards = ${result.metersToDeduct}m (includes 5% wastage: +${wastageAmount}m)`;
        }
    }
}

/**
 * Update stock warning display
 * @param {Object} elements - DOM elements
 * @param {Object} result - Calculation result
 * @param {boolean} isError - Whether there's an error
 */
function updateStockWarning(elements, result, isError) {
    if (elements.stockWarning) {
        const warning = typeof elements.stockWarning === 'string'
            ? document.getElementById(elements.stockWarning)
            : elements.stockWarning;
        
        if (warning) {
            if (isError) {
                warning.textContent = `Insufficient Stock! Available: ${result.currentStock}, Required: ${result.calculatedTotal}`;
                warning.className = 'stock-warning error';
                warning.style.display = 'block';
            } else {
                warning.textContent = `Available: ${result.currentStock} | Required: ${result.calculatedTotal}`;
                warning.className = 'stock-warning success';
                warning.style.display = 'block';
            }
        }
    }
    
    // Also update the meters/kit fields with red color if insufficient
    if (isError) {
        if (elements.metersToDeduct) {
            const field = typeof elements.metersToDeduct === 'string'
                ? document.getElementById(elements.metersToDeduct)
                : elements.metersToDeduct;
            if (field) field.classList.add('insufficient-stock');
        }
        
        if (elements.hardenerRequired) {
            const field = typeof elements.hardenerRequired === 'string'
                ? document.getElementById(elements.hardenerRequired)
                : elements.hardenerRequired;
            if (field) field.classList.add('insufficient-stock');
        }
        
        if (elements.thinnerRequired) {
            const field = typeof elements.thinnerRequired === 'string'
                ? document.getElementById(elements.thinnerRequired)
                : elements.thinnerRequired;
            if (field) field.classList.add('insufficient-stock');
        }
    }
}

/**
 * Disable confirm sale button
 * @param {Object} elements - DOM elements
 */
function disableConfirmButton(elements) {
    if (elements.confirmButton) {
        const button = typeof elements.confirmButton === 'string'
            ? document.getElementById(elements.confirmButton)
            : elements.confirmButton;
        
        if (button) {
            button.disabled = true;
            button.classList.add('disabled');
            button.title = 'Insufficient stock - cannot confirm sale';
        }
    }
}

/**
 * Enable confirm sale button
 * @param {Object} elements - DOM elements
 */
function enableConfirmButton(elements) {
    if (elements.confirmButton) {
        const button = typeof elements.confirmButton === 'string'
            ? document.getElementById(elements.confirmButton)
            : elements.confirmButton;
        
        if (button) {
            button.disabled = false;
            button.classList.remove('disabled');
            button.title = 'Click to confirm sale';
        }
    }
}

/**
 * Clear kit-related fields
 * @param {Object} elements - DOM elements
 */
function clearKitFields(elements) {
    if (elements.hardenerRequired) {
        const field = typeof elements.hardenerRequired === 'string'
            ? document.getElementById(elements.hardenerRequired)
            : elements.hardenerRequired;
        if (field) field.value = '';
    }
    
    if (elements.thinnerRequired) {
        const field = typeof elements.thinnerRequired === 'string'
            ? document.getElementById(elements.thinnerRequired)
            : elements.thinnerRequired;
        if (field) field.value = '';
    }
}

/**
 * Clear carpet-related fields
 * @param {Object} elements - DOM elements
 */
function clearCarpetFields(elements) {
    if (elements.metersToDeduct) {
        const field = typeof elements.metersToDeduct === 'string'
            ? document.getElementById(elements.metersToDeduct)
            : elements.metersToDeduct;
        if (field) {
            field.value = '';
            field.placeholder = '';
        }
    }
}

/**
 * Clear all preview fields
 * @param {Object} elements - DOM elements
 */
function clearPreviewFields(elements) {
    clearKitFields(elements);
    clearCarpetFields(elements);
    
    if (elements.stockWarning) {
        const warning = typeof elements.stockWarning === 'string'
            ? document.getElementById(elements.stockWarning)
            : elements.stockWarning;
        if (warning) warning.style.display = 'none';
    }
}

// =============================================================================
// EVENT LISTENER SETUP
// =============================================================================

/**
 * Create event listeners for sale input
 * @param {Object} config - Configuration object
 * @returns {Object} Cleanup function
 */
function setupSaleInputListeners(config) {
    const {
        quantityInput,
        productSelect,
        unitSelect,
        onProductChange,
        onQuantityChange,
        onUnitChange,
        fetchProductData,
        elements
    } = config;

    const cleanupFunctions = [];

    // Quantity input listener
    if (quantityInput) {
        const quantityEl = typeof quantityInput === 'string' 
            ? document.getElementById(quantityInput) 
            : quantityInput;
        
        if (quantityEl) {
            const handler = (e) => {
                const quantity = parseFloat(e.target.value) || 0;
                
                if (onQuantityChange) {
                    onQuantityChange(quantity);
                }
                
                // Auto-trigger calculation if we have product data
                if (config.currentProduct && quantity > 0) {
                    handleSaleInput({
                        product: config.currentProduct,
                        quantity: quantity,
                        unitSelected: unitSelect ? 
                            (typeof unitSelect === 'string' ? document.getElementById(unitSelect)?.value : unitSelect.value) 
                            : '',
                        elements: elements
                    });
                }
            };
            
            quantityEl.addEventListener('input', handler);
            cleanupFunctions.push(() => quantityEl.removeEventListener('input', handler));
        }
    }

    // Product select listener
    if (productSelect) {
        const productEl = typeof productSelect === 'string'
            ? document.getElementById(productSelect)
            : productSelect;
        
        if (productEl) {
            const handler = async (e) => {
                const productId = e.target.value;
                
                // Clear previous data
                clearPreviewFields(elements);
                
                if (!productId) {
                    if (onProductChange) onProductChange(null);
                    config.currentProduct = null;
                    return;
                }
                
                // Fetch product data
                let product = null;
                if (fetchProductData) {
                    product = await fetchProductData(productId);
                } else {
                    // Default fetch using API
                    product = await defaultFetchProduct(productId);
                }
                
                config.currentProduct = product;
                
                if (onProductChange) onProductChange(product);
                
                // Auto-trigger calculation if quantity is already entered
                const quantity = quantityInput ? 
                    (typeof quantityInput === 'string' ? document.getElementById(quantityInput)?.value : quantityInput.value)
                    : 0;
                
                if (product && quantity > 0) {
                    handleSaleInput({
                        product: product,
                        quantity: parseFloat(quantity),
                        unitSelected: unitSelect ? 
                            (typeof unitSelect === 'string' ? document.getElementById(unitSelect)?.value : unitSelect.value) 
                            : '',
                        elements: elements
                    });
                }
            };
            
            productEl.addEventListener('change', handler);
            cleanupFunctions.push(() => productEl.removeEventListener('change', handler));
        }
    }

    // Unit select listener
    if (unitSelect) {
        const unitEl = typeof unitSelect === 'string'
            ? document.getElementById(unitSelect)
            : unitSelect;
        
        if (unitEl) {
            const handler = (e) => {
                const unit = e.target.value;
                
                if (onUnitChange) onUnitChange(unit);
                
                // Auto-trigger calculation if we have product and quantity
                if (config.currentProduct && quantityInput) {
                    const quantity = typeof quantityInput === 'string' 
                        ? document.getElementById(quantityInput)?.value 
                        : quantityInput.value;
                    
                    if (quantity && parseFloat(quantity) > 0) {
                        handleSaleInput({
                            product: config.currentProduct,
                            quantity: parseFloat(quantity),
                            unitSelected: unit,
                            elements: elements
                        });
                    }
                }
            };
            
            unitEl.addEventListener('change', handler);
            cleanupFunctions.push(() => unitEl.removeEventListener('change', handler));
        }
    }

    // Return cleanup function
    return function cleanup() {
        cleanupFunctions.forEach(fn => fn());
    };
}

/**
 * Default product fetch function
 * @param {string} productId - Product UUID
 * @returns {Promise<Object>} Product data
 */
async function defaultFetchProduct(productId) {
    try {
        const response = await fetch(`/api/products/${productId}`);
        if (!response.ok) {
            throw new Error('Failed to fetch product');
        }
        return await response.json();
    } catch (error) {
        console.error('Error fetching product:', error);
        return null;
    }
}

// =============================================================================
// EXAMPLE USAGE & INITIALIZATION
// =============================================================================

/**
 * Example: Initialize sale input handler for Staff Site
 * @param {Object} options - Initialization options
 */
function initSaleInputHandler(options = {}) {
    const {
        quantityInputId = 'quantity',
        productSelectId = 'product',
        unitSelectId = 'unit',
        hardenerFieldId = 'hardener_required',
        thinnerFieldId = 'thinner_required',
        metersFieldId = 'meters_to_deduct',
        confirmButtonId = 'confirm_sale_btn',
        stockWarningId = 'stock_warning'
    } = options;

    // Define elements
    const elements = {
        quantityInput: quantityInputId,
        productSelect: productSelectId,
        unitSelect: unitSelectId,
        hardenerRequired: hardenerFieldId,
        thinnerRequired: thinnerFieldId,
        metersToDeduct: metersFieldId,
        confirmButton: confirmButtonId,
        stockWarning: stockWarningId
    };

    // Configuration object
    const config = {
        quantityInput: quantityInputId,
        productSelect: productSelectId,
        unitSelect: unitSelectId,
        elements: elements,
        currentProduct: null,
        fetchProductData: async (productId) => {
            return await defaultFetchProduct(productId);
        }
    };

    // Set up event listeners
    const cleanup = setupSaleInputListeners(config);

    console.log('Sale Input Handler initialized successfully!');
    console.log('Element IDs:', elements);

    return {
        cleanup,
        handleSaleInput: (opts) => handleSaleInput({ ...opts, elements }),
        config
    };
}

// =============================================================================
// EXPORTS
// =============================================================================

// Export for different module systems
if (typeof module !== 'undefined' && module.exports) {
    // Node.js / CommonJS
    module.exports = {
        handleSaleInput,
        setupSaleInputListeners,
        initSaleInputHandler,
        yardsToMeters,
        inchesToMeters,
        calculateWithWastage,
        isCarpetCategory,
        isYardsUnit,
        SALE_INPUT_CONFIG
    };
} else if (typeof window !== 'undefined') {
    // Browser global
    window.handleSaleInput = handleSaleInput;
    window.setupSaleInputListeners = setupSaleInputListeners;
    window.initSaleInputHandler = initSaleInputHandler;
    window.SALE_INPUT_CONFIG = SALE_INPUT_CONFIG;
} else {
    // ES Module
    export {
        handleSaleInput,
        setupSaleInputListeners,
        initSaleInputHandler,
        yardsToMeters,
        inchesToMeters,
        calculateWithWastage,
        isCarpetCategory,
        isYardsUnit,
        SALE_INPUT_CONFIG
    };
}

// =============================================================================
// EXAMPLE HTML MARKUP (for reference)
// =============================================================================

/*
<!-- Example HTML Structure for Staff Site -->

<div class="sale-form">
    <h2>New Sale</h2>
    
    <!-- Product Selection -->
    <div class="form-group">
        <label for="product">Select Product:</label>
        <select id="product" name="product" required>
            <option value="">-- Select Product --</option>
            <!-- Products loaded from API -->
        </select>
    </div>
    
    <!-- Current Stock Display -->
    <div class="form-group">
        <label>Current Stock:</label>
        <span id="current_stock" class="stock-display">--</span>
    </div>
    
    <!-- Unit Selection -->
    <div class="form-group">
        <label for="unit">Unit:</label>
        <select id="unit" name="unit" required>
            <option value="yards">Yards</option>
            <option value="inches">Inches</option>
            <option value="lts">Liters</option>
            <option value="kg">Kilograms</option>
            <option value="pcs">Pieces</option>
        </select>
    </div>
    
    <!-- Quantity Input -->
    <div class="form-group">
        <label for="quantity">Quantity:</label>
        <input type="number" id="quantity" name="quantity" 
               min="0" step="0.01" required placeholder="Enter quantity">
    </div>
    
    <!-- Kit Fields (read-only, auto-populated) -->
    <div id="kit_fields" class="form-group" style="display: none;">
        <label>Hardener Required:</label>
        <input type="text" id="hardener_required" readonly 
               class="read-only-field" placeholder="Auto-calculated">
        
        <label>Thinner Required:</label>
        <input type="text" id="thinner_required" readonly 
               class="read-only-field" placeholder="Auto-calculated">
    </div>
    
    <!-- Carpet Preview (shows meters to deduct) -->
    <div id="carpet_preview" class="form-group" style="display: none;">
        <label>Total Meters to be Deducted:</label>
        <input type="text" id="meters_to_deduct" readonly 
               class="preview-field" placeholder="Includes 5% wastage">
        <small class="hint">Includes 5% aviation cutting wastage</small>
    </div>
    
    <!-- Stock Warning -->
    <div id="stock_warning" class="stock-warning" style="display: none;"></div>
    
    <!-- Confirm Button -->
    <button type="button" id="confirm_sale_btn" disabled>
        Confirm Sale
    </button>
</div>

<style>
    .stock-warning {
        padding: 10px;
        border-radius: 4px;
        margin: 10px 0;
    }
    .stock-warning.error {
        background-color: #ffebee;
        color: #c62828;
        border: 1px solid #c62828;
    }
    .stock-warning.success {
        background-color: #e8f5e9;
        color: #2e7d32;
        border: 1px solid #2e7d32;
    }
    .insufficient-stock {
        color: #c62828;
        font-weight: bold;
        border-color: #c62828 !important;
    }
    .read-only-field {
        background-color: #f5f5f5;
        border: 1px solid #ddd;
        padding: 8px;
        border-radius: 4px;
    }
    .preview-field {
        background-color: #e3f2fd;
        border: 1px solid #1976d2;
        padding: 8px;
        border-radius: 4px;
        font-weight: bold;
    }
    button:disabled {
        opacity: 0.5;
        cursor: not-allowed;
    }
</style>

<script src="handleSaleInput.js"></script>
<script>
    // Initialize on page load
    document.addEventListener('DOMContentLoaded', function() {
        initSaleInputHandler({
            quantityInputId: 'quantity',
            productSelectId: 'product',
            unitSelectId: 'unit',
            hardenerFieldId: 'hardener_required',
            thinnerFieldId: 'thinner_required',
            metersFieldId: 'meters_to_deduct',
            confirmButtonId: 'confirm_sale_btn',
            stockWarningId: 'stock_warning'
        });
    });
</script>
*/

