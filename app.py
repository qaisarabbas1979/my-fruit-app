-- 1. Gas Supplier Ledger (Money)
CREATE TABLE gas_supplier_bills (
    id int8 primary key generated always as identity,
    supplier_name text,
    bill_amount float8,
    paid_amount float8,
    full_bottles_received int8,
    date text
);

-- 2. Empty Bottles Return Tracker (Physical)
CREATE TABLE gas_supplier_returns (
    id int8 primary key generated always as identity,
    supplier_name text,
    empties_returned int8,
    date text
);
