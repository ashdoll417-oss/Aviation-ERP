/**
 * Node.js script to test Supabase connection and list all tables
 * 
 * Usage:
 *   npm install pg
 *   node check_supabase_tables.js
 * 
 * Or set environment variables and run:
 *   node check_supabase_tables.js
 */

const { Pool } = require('pg');

// Get connection string from environment or use a default
const DATABASE_URL = process.env.DATABASE_URL || process.env.HEROKU_POSTGRESQL_COPPER_URL;

async function main() {
  if (!DATABASE_URL) {
    console.error('Error: DATABASE_URL environment variable not set');
    console.log('Please set DATABASE_URL or HEROKU_POSTGRESQL_COPPER_URL');
    process.exit(1);
  }

  console.log('Connecting to Supabase/PostgreSQL...');
  console.log('Connection URL:', DATABASE_URL.replace(/:[^:@]+@/, ':****@')); // Hide password
  
  const pool = new Pool({
    connectionString: DATABASE_URL,
    ssl: {
      rejectUnauthorized: false // Required for Heroku/Render
    }
  });

  try {
    // Test connection
    const client = await pool.connect();
    console.log('\n✓ Connection successful!\n');

    // Check search_path
    console.log('=== Checking search_path ===');
    const searchPathResult = await client.query('SHOW search_path');
    console.log('Current search_path:', searchPathResult.rows[0].search_path);

    // List all tables in public schema
    console.log('\n=== Tables in public schema ===');
    const tablesResult = await client.query(`
      SELECT table_name 
      FROM information_schema.tables 
      WHERE table_schema = 'public' 
      AND table_type = 'BASE TABLE'
      ORDER BY table_name
    `);
    
    if (tablesResult.rows.length === 0) {
      console.log('No tables found in public schema!');
    } else {
      console.log(`Found ${tablesResult.rows.length} table(s):`);
      tablesResult.rows.forEach((row, index) => {
        console.log(`  ${index + 1}. ${row.table_name}`);
      });
    }

    // List all views
    console.log('\n=== Views in public schema ===');
    const viewsResult = await client.query(`
      SELECT table_name 
      FROM information_schema.views 
      WHERE table_schema = 'public'
      ORDER BY table_name
    `);
    
    if (viewsResult.rows.length === 0) {
      console.log('No views found in public schema');
    } else {
      console.log(`Found ${viewsResult.rows.length} view(s):`);
      viewsResult.rows.forEach((row, index) => {
        console.log(`  ${index + 1}. ${row.table_name}`);
      });
    }

    // List all sequences
    console.log('\n=== Sequences in public schema ===');
    const sequencesResult = await client.query(`
      SELECT sequence_name 
      FROM information_schema.sequences 
      WHERE sequence_schema = 'public'
      ORDER BY sequence_name
    `);
    
    if (sequencesResult.rows.length === 0) {
      console.log('No sequences found in public schema');
    } else {
      console.log(`Found ${sequencesResult.rows.length} sequence(s):`);
      sequencesResult.rows.forEach((row, index) => {
        console.log(`  ${index + 1}. ${row.sequence_name}`);
      });
    }

    // Check all schemas
    console.log('\n=== All schemas ===');
    const schemasResult = await client.query(`
      SELECT schema_name 
      FROM information_schema.schemata 
      WHERE schema_name NOT IN ('pg_catalog', 'information_schema')
      ORDER BY schema_name
    `);
    
    if (schemasResult.rows.length === 0) {
      console.log('No custom schemas found');
    } else {
      console.log(`Found ${schemasResult.rows.length} schema(s):`);
      schemasResult.rows.forEach((row, index) => {
        console.log(`  ${index + 1}. ${row.schema_name}`);
      });
    }

    // Check if suppliers table exists in any schema
    console.log('\n=== Searching for "suppliers" table ===');
    const suppliersSearch = await client.query(`
      SELECT table_schema, table_name 
      FROM information_schema.tables 
      WHERE table_name = 'suppliers'
      OR table_name LIKE '%supplier%'
    `);
    
    if (suppliersSearch.rows.length === 0) {
      console.log('No table with "suppliers" in name found!');
    } else {
      console.log('Found suppliers table(s):');
      suppliersSearch.rows.forEach((row) => {
        console.log(`  - ${row.table_schema}.${row.table_name}`);
      });
    }

    client.release();
    console.log('\n✓ Script completed successfully!');
    
  } catch (error) {
    console.error('\n✗ Error:', error.message);
    
    // Provide helpful suggestions based on error
    if (error.code === '42P01') {
      console.log('\n=== Troubleshooting ===');
      console.log('Error 42P01 means "relation does not exist"');
      console.log('Possible causes:');
      console.log('  1. Table not created yet in the database');
      console.log('  2. Table is in a different schema');
      console.log('  3. Using wrong database connection');
      console.log('\nSuggestions:');
      console.log('  - Check if tables exist in public schema (shown above)');
      console.log('  - Verify DATABASE_URL points to correct database');
      console.log('  - Run SQL migrations to create tables');
    }
    
  } finally {
    await pool.end();
  }
}

main();

