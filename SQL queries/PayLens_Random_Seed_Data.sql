/*
PayLens - randomized synthetic SQL Server / Azure SQL seed data
=============================================================
Rows: 5 merchants, 200 customers, 278 customer payment methods,
      8 merchant payout accounts.
Generation seed: 3103459737446081020

HOW TO RUN
1. Create the four dbo tables using the schemas discussed in this chat.
2. Open this UTF-8 file in Azure SQL Query editor or SSMS.
3. Run the ENTIRE file together, with no text selected.

SCHEMA ASSUMPTIONS
- customers uses firstName NVARCHAR(75) NULL and secondName NVARCHAR(75) NULL.
  Customer names are English transliterations in two separate columns.
- If customers still has only full_name, run this ONCE in a SEPARATE query
  before running this file (or update your original CREATE TABLE):

    ALTER TABLE dbo.customers ADD
        firstName NVARCHAR(75) NULL,
        secondName NVARCHAR(75) NULL;

  This optional ADD preserves any existing full_name data. The seed INSERT
  below uses only firstName and secondName. No ALTER runs from this comment.
- customers includes merchant_id, customer_reference, city, limits_currency,
  max_transaction_amount_minor, max_daily_spend_minor and require_3ds.
- customer_payment_methods uses processor_code and
  processor_account_reference (not the earlier provider_* column names).
- All four tables have their IDENTITY primary keys and created_at columns.
- updated_at is omitted and remains NULL for these newly inserted rows.

DATA NOTES
- Names, phone numbers, account numbers and tokens are synthetic test data.
- Emails use reserved example.com domains. Do not contact these phone numbers.
- PROC_A is the only fictional processor. No token can execute a payment.
- All monetary limits / fixed fees use EGP piastres: 100 minor units = 1 EGP.
- All settlement, limit and payout currencies are EGP in this dataset.
- All eight payout accounts have non-empty synthetic Egyptian-format IBANs.
  Their format is 29 characters and their MOD-97 checksum is valid.
  The 990x bank identifiers and branch identifiers are invented test values,
  not verified routing information for the displayed bank names.
  The IBAN account component uses the same mock account identifier normalized
  to 17 digits; the original account_number keeps its extra leading padding.
  These values are test fixtures, not verified bank-issued IBANs.
  SWIFT remains optional and NULL.
  Format reference: https://www.cbe.org.eg/en/payment-systems-and-services/payment-systems/iban
- One active default EGP payout account is generated per merchant.
- New IDENTITY values are captured with OUTPUT. IDs need not start at 1.
- No table is dropped, cleared or recreated. Existing rows are preserved.
- Re-running THIS same file is blocked by its merchant-name guard.
- Data is already randomly generated; this file contains fixed VALUES.
*/

SET NOCOUNT ON;
SET XACT_ABORT ON;

DECLARE @SeedMerchants TABLE (
    merchant_id BIGINT PRIMARY KEY,
    business_name NVARCHAR(150) NOT NULL UNIQUE
);
DECLARE @SeedCustomers TABLE (
    customer_id BIGINT PRIMARY KEY,
    customer_reference NVARCHAR(100) NOT NULL UNIQUE
);
DECLARE @SeedMethods TABLE (payment_method_id BIGINT PRIMARY KEY);
DECLARE @SeedPayoutAccounts TABLE (payout_account_id BIGINT PRIMARY KEY);

BEGIN TRY
    BEGIN TRANSACTION;

    IF EXISTS (
        SELECT 1 FROM dbo.merchants
        WHERE business_name IN (N'Nile Electronics', N'Alex Fashion', N'Delta Market', N'Cairo Home', N'Red Sea Sports')
    )
    BEGIN
        THROW 50001, 'This seed batch already exists (or a merchant name is in use). No rows were added.', 1;
    END;

    -- 1. Merchants: parent records are inserted first.
    INSERT INTO dbo.merchants (
        business_name, legal_name, business_category, email, phone_number, country_code, city, settlement_currency, commission_rate_percent, fixed_fee_minor, payout_frequency, status, created_at
    )
    OUTPUT inserted.merchant_id, inserted.business_name INTO @SeedMerchants (merchant_id, business_name)
    VALUES
        (N'Nile Electronics', N'Nile Electronics Trading LLC', N'Electronics', N'merchant1@paylens.example.com', N'+201004719344', N'EG', N'Cairo', N'EGP', 2.75, 100, N'daily', N'active', '2025-10-19T13:00:00.000'),
        (N'Alex Fashion', N'Alex Fashion Trading LLC', N'Fashion', N'merchant2@paylens.example.com', N'+201066348306', N'EG', N'Alexandria', N'EGP', 2.5, 200, N'daily', N'active', '2025-03-26T12:00:00.000'),
        (N'Delta Market', N'Delta Retail LLC', N'Groceries', N'merchant3@paylens.example.com', N'+201048974564', N'EG', N'Mansoura', N'EGP', 2.75, 200, N'daily', N'active', '2025-05-02T04:00:00.000'),
        (N'Cairo Home', N'Cairo Home Supplies LLC', N'Home and Furniture', N'merchant4@paylens.example.com', N'+201007097405', N'EG', N'Giza', N'EGP', 1.5, 100, N'daily', N'active', '2025-06-10T04:00:00.000'),
        (N'Red Sea Sports', N'Red Sea Sports Trading LLC', N'Sports', N'merchant5@paylens.example.com', N'+201093301732', N'EG', N'Hurghada', N'EGP', 2.5, 200, N'weekly', N'suspended', '2025-11-01T14:00:00.000');

    -- 2. Customers: each customer belongs to one of the five new merchants.
    INSERT INTO dbo.customers (
        merchant_id, customer_reference, firstName, secondName, email, phone_number, country_code, city, limits_currency, max_transaction_amount_minor, max_daily_spend_minor, require_3ds, created_at
    )
    OUTPUT inserted.customer_id, inserted.customer_reference INTO @SeedCustomers (customer_id, customer_reference)
    VALUES
        ((SELECT merchant_id FROM @SeedMerchants WHERE business_name = N'Cairo Home'), N'DEMO-PL-C0001', N'Salma', N'Morad', N'customer001@paylens.example.com', N'+201572989608', N'EG', N'Aswan', N'EGP', 1000000, 3000000, 0, '2026-07-19T13:26:00.000'),
        ((SELECT merchant_id FROM @SeedMerchants WHERE business_name = N'Red Sea Sports'), N'DEMO-PL-C0002', N'Hussein', N'Morad', N'customer002@paylens.example.com', N'+201159489320', N'EG', N'Assiut', N'EGP', 250000, 1250000, 0, '2026-09-13T00:00:00.000'),
        ((SELECT merchant_id FROM @SeedMerchants WHERE business_name = N'Nile Electronics'), N'DEMO-PL-C0003', N'Yassin', N'Ibrahim', N'customer003@paylens.example.com', N'+201502319080', N'EG', N'Hurghada', N'EGP', 50000, 200000, 0, '2026-05-06T06:09:00.000'),
        ((SELECT merchant_id FROM @SeedMerchants WHERE business_name = N'Red Sea Sports'), N'DEMO-PL-C0004', N'Ali', N'Samir', N'customer004@paylens.example.com', N'+201599181440', N'EG', N'Alexandria', N'EGP', 1000000, 3000000, 0, '2026-04-15T17:21:00.000'),
        ((SELECT merchant_id FROM @SeedMerchants WHERE business_name = N'Delta Market'), N'DEMO-PL-C0005', N'Salma', N'Refaat', N'customer005@paylens.example.com', N'+201273584162', N'EG', N'Aswan', N'EGP', 500000, 2500000, 0, '2026-04-15T11:22:00.000'),
        ((SELECT merchant_id FROM @SeedMerchants WHERE business_name = N'Nile Electronics'), N'DEMO-PL-C0006', N'Fatma', N'Othman', N'customer006@paylens.example.com', N'+201268796609', N'EG', N'Giza', N'EGP', 100000, 300000, 0, '2026-08-09T15:08:00.000'),
        ((SELECT merchant_id FROM @SeedMerchants WHERE business_name = N'Alex Fashion'), N'DEMO-PL-C0007', N'Heba', N'Abdallah', N'customer007@paylens.example.com', N'+201044466050', N'EG', N'Mansoura', N'EGP', 50000, 200000, 0, '2026-08-10T04:27:00.000'),
        ((SELECT merchant_id FROM @SeedMerchants WHERE business_name = N'Red Sea Sports'), N'DEMO-PL-C0008', N'Menna', N'Kamal', N'customer008@paylens.example.com', N'+201545595513', N'EG', N'Giza', N'EGP', 50000, 100000, 0, '2026-08-03T13:36:00.000'),
        ((SELECT merchant_id FROM @SeedMerchants WHERE business_name = N'Delta Market'), N'DEMO-PL-C0009', N'Eman', N'Morad', N'customer009@paylens.example.com', N'+201106170735', N'EG', N'Alexandria', N'EGP', 500000, 2000000, 0, '2026-10-29T22:22:00.000'),
        ((SELECT merchant_id FROM @SeedMerchants WHERE business_name = N'Cairo Home'), N'DEMO-PL-C0010', N'Mostafa', N'Saeed', N'customer010@paylens.example.com', N'+201527965580', N'EG', N'Mansoura', N'EGP', 1000000, 3000000, 0, '2026-08-24T07:18:00.000'),
        ((SELECT merchant_id FROM @SeedMerchants WHERE business_name = N'Red Sea Sports'), N'DEMO-PL-C0011', N'Shaimaa', N'Farouk', N'customer011@paylens.example.com', N'+201279328223', N'EG', N'Alexandria', N'EGP', 250000, 750000, 0, '2026-07-02T12:16:00.000'),
        ((SELECT merchant_id FROM @SeedMerchants WHERE business_name = N'Nile Electronics'), N'DEMO-PL-C0012', N'Nada', N'Hamdy', N'customer012@paylens.example.com', N'+201146158311', N'EG', N'Cairo', N'EGP', 2000000, 6000000, 0, '2026-06-03T12:51:00.000'),
        ((SELECT merchant_id FROM @SeedMerchants WHERE business_name = N'Delta Market'), N'DEMO-PL-C0013', N'Shaimaa', N'Soliman', N'customer013@paylens.example.com', N'+201236077922', N'EG', N'Assiut', N'EGP', 2000000, 10000000, 0, '2026-10-13T13:10:00.000'),
        ((SELECT merchant_id FROM @SeedMerchants WHERE business_name = N'Red Sea Sports'), N'DEMO-PL-C0014', N'Nada', N'Saeed', N'customer014@paylens.example.com', N'+201031914989', N'EG', N'Assiut', N'EGP', 1000000, 5000000, 0, '2026-06-05T03:33:00.000'),
        ((SELECT merchant_id FROM @SeedMerchants WHERE business_name = N'Nile Electronics'), N'DEMO-PL-C0015', N'Asmaa', N'Ali', N'customer015@paylens.example.com', N'+201262567522', N'EG', N'Cairo', N'EGP', 500000, 1500000, 0, '2026-09-14T19:33:00.000'),
        ((SELECT merchant_id FROM @SeedMerchants WHERE business_name = N'Nile Electronics'), N'DEMO-PL-C0016', N'Heba', N'Saeed', N'customer016@paylens.example.com', N'+201133116581', N'EG', N'Alexandria', N'EGP', 50000, 150000, 0, '2026-08-01T03:50:00.000'),
        ((SELECT merchant_id FROM @SeedMerchants WHERE business_name = N'Delta Market'), N'DEMO-PL-C0017', N'Shaimaa', N'Kamal', N'customer017@paylens.example.com', N'+201574843133', N'EG', N'Port Said', N'EGP', 250000, 750000, 0, '2026-09-17T22:56:00.000'),
        ((SELECT merchant_id FROM @SeedMerchants WHERE business_name = N'Red Sea Sports'), N'DEMO-PL-C0018', N'Ibrahim', N'Ibrahim', N'customer018@paylens.example.com', N'+201137820970', N'EG', N'Ismailia', N'EGP', 250000, 1000000, 0, '2026-10-24T00:33:00.000'),
        ((SELECT merchant_id FROM @SeedMerchants WHERE business_name = N'Nile Electronics'), N'DEMO-PL-C0019', N'Hassan', N'Fouad', N'customer019@paylens.example.com', N'+201196681954', N'EG', N'Tanta', N'EGP', 250000, 500000, 0, '2026-10-20T02:31:00.000'),
        ((SELECT merchant_id FROM @SeedMerchants WHERE business_name = N'Cairo Home'), N'DEMO-PL-C0020', N'Khaled', N'Morad', N'customer020@paylens.example.com', N'+201261560371', N'EG', N'Ismailia', N'EGP', 250000, 500000, 0, '2026-09-12T00:07:00.000'),
        ((SELECT merchant_id FROM @SeedMerchants WHERE business_name = N'Red Sea Sports'), N'DEMO-PL-C0021', N'Amr', N'Ibrahim', N'customer021@paylens.example.com', N'+201154979292', N'EG', N'Port Said', N'EGP', 2000000, 6000000, 1, '2026-06-27T00:02:00.000'),
        ((SELECT merchant_id FROM @SeedMerchants WHERE business_name = N'Red Sea Sports'), N'DEMO-PL-C0022', N'Karim', N'Hamdy', N'customer022@paylens.example.com', N'+201290206670', N'EG', N'Ismailia', N'EGP', 1000000, 3000000, 1, '2026-10-26T18:16:00.000'),
        ((SELECT merchant_id FROM @SeedMerchants WHERE business_name = N'Delta Market'), N'DEMO-PL-C0023', N'Yasmin', N'Kamal', N'customer023@paylens.example.com', N'+201125993632', N'EG', N'Assiut', N'EGP', 1000000, 3000000, 1, '2026-06-05T09:42:00.000'),
        ((SELECT merchant_id FROM @SeedMerchants WHERE business_name = N'Nile Electronics'), N'DEMO-PL-C0024', N'Fatma', N'Mansour', N'customer024@paylens.example.com', N'+201025949760', N'EG', N'Mansoura', N'EGP', 100000, 300000, 0, '2026-06-14T05:26:00.000'),
        ((SELECT merchant_id FROM @SeedMerchants WHERE business_name = N'Delta Market'), N'DEMO-PL-C0025', N'Menna', N'Fouad', N'customer025@paylens.example.com', N'+201222087027', N'EG', N'Aswan', N'EGP', 50000, 150000, 0, '2026-06-21T21:09:00.000'),
        ((SELECT merchant_id FROM @SeedMerchants WHERE business_name = N'Delta Market'), N'DEMO-PL-C0026', N'Nour', N'Hamdy', N'customer026@paylens.example.com', N'+201192635707', N'EG', N'Mansoura', N'EGP', 1000000, 5000000, 0, '2026-08-06T10:16:00.000'),
        ((SELECT merchant_id FROM @SeedMerchants WHERE business_name = N'Nile Electronics'), N'DEMO-PL-C0027', N'Dina', N'Hamdy', N'customer027@paylens.example.com', N'+201247139237', N'EG', N'Tanta', N'EGP', 2000000, 8000000, 0, '2026-10-07T19:50:00.000'),
        ((SELECT merchant_id FROM @SeedMerchants WHERE business_name = N'Cairo Home'), N'DEMO-PL-C0028', N'Nada', N'Saeed', N'customer028@paylens.example.com', N'+201546698231', N'EG', N'Mansoura', N'EGP', 2000000, 10000000, 0, '2026-07-26T10:26:00.000'),
        ((SELECT merchant_id FROM @SeedMerchants WHERE business_name = N'Alex Fashion'), N'DEMO-PL-C0029', N'Amr', N'Farouk', N'customer029@paylens.example.com', N'+201256545660', N'EG', N'Alexandria', N'EGP', 50000, 150000, 1, '2026-07-16T16:22:00.000'),
        ((SELECT merchant_id FROM @SeedMerchants WHERE business_name = N'Delta Market'), N'DEMO-PL-C0030', N'Eman', N'Hassan', N'customer030@paylens.example.com', N'+201189050936', N'EG', N'Tanta', N'EGP', 50000, 200000, 1, '2026-06-05T15:56:00.000'),
        ((SELECT merchant_id FROM @SeedMerchants WHERE business_name = N'Delta Market'), N'DEMO-PL-C0031', N'Mahmoud', N'Mansour', N'customer031@paylens.example.com', N'+201226111699', N'EG', N'Port Said', N'EGP', 100000, 200000, 0, '2026-05-28T11:14:00.000'),
        ((SELECT merchant_id FROM @SeedMerchants WHERE business_name = N'Alex Fashion'), N'DEMO-PL-C0032', N'Aya', N'Fouad', N'customer032@paylens.example.com', N'+201548515970', N'EG', N'Port Said', N'EGP', 100000, 300000, 0, '2026-05-06T04:08:00.000'),
        ((SELECT merchant_id FROM @SeedMerchants WHERE business_name = N'Red Sea Sports'), N'DEMO-PL-C0033', N'Hassan', N'Saleh', N'customer033@paylens.example.com', N'+201120066964', N'EG', N'Port Said', N'EGP', 2000000, 4000000, 0, '2026-06-27T05:13:00.000'),
        ((SELECT merchant_id FROM @SeedMerchants WHERE business_name = N'Nile Electronics'), N'DEMO-PL-C0034', N'Ahmed', N'Hamdy', N'customer034@paylens.example.com', N'+201010943143', N'EG', N'Port Said', N'EGP', 100000, 300000, 1, '2026-09-06T06:08:00.000'),
        ((SELECT merchant_id FROM @SeedMerchants WHERE business_name = N'Red Sea Sports'), N'DEMO-PL-C0035', N'Heba', N'Hassan', N'customer035@paylens.example.com', N'+201170287431', N'EG', N'Ismailia', N'EGP', 500000, 1000000, 0, '2026-05-10T02:53:00.000'),
        ((SELECT merchant_id FROM @SeedMerchants WHERE business_name = N'Cairo Home'), N'DEMO-PL-C0036', N'Sara', N'Ali', N'customer036@paylens.example.com', N'+201568218622', N'EG', N'Assiut', N'EGP', 250000, 750000, 0, '2026-05-11T21:48:00.000'),
        ((SELECT merchant_id FROM @SeedMerchants WHERE business_name = N'Alex Fashion'), N'DEMO-PL-C0037', N'Salma', N'Samir', N'customer037@paylens.example.com', N'+201503965986', N'EG', N'Giza', N'EGP', 50000, 250000, 0, '2026-07-12T02:11:00.000'),
        ((SELECT merchant_id FROM @SeedMerchants WHERE business_name = N'Red Sea Sports'), N'DEMO-PL-C0038', N'Asmaa', N'Mansour', N'customer038@paylens.example.com', N'+201211717794', N'EG', N'Alexandria', N'EGP', 250000, 750000, 1, '2026-04-14T15:34:00.000'),
        ((SELECT merchant_id FROM @SeedMerchants WHERE business_name = N'Red Sea Sports'), N'DEMO-PL-C0039', N'Shaimaa', N'Ali', N'customer039@paylens.example.com', N'+201562464341', N'EG', N'Giza', N'EGP', 100000, 300000, 0, '2026-09-25T14:28:00.000'),
        ((SELECT merchant_id FROM @SeedMerchants WHERE business_name = N'Red Sea Sports'), N'DEMO-PL-C0040', N'Ibrahim', N'Samir', N'customer040@paylens.example.com', N'+201118368964', N'EG', N'Ismailia', N'EGP', 100000, 200000, 0, '2026-07-20T01:50:00.000'),
        ((SELECT merchant_id FROM @SeedMerchants WHERE business_name = N'Nile Electronics'), N'DEMO-PL-C0041', N'Shaimaa', N'Refaat', N'customer041@paylens.example.com', N'+201170541050', N'EG', N'Alexandria', N'EGP', 1000000, 2000000, 1, '2026-10-20T17:04:00.000'),
        ((SELECT merchant_id FROM @SeedMerchants WHERE business_name = N'Red Sea Sports'), N'DEMO-PL-C0042', N'Heba', N'Morad', N'customer042@paylens.example.com', N'+201203692166', N'EG', N'Alexandria', N'EGP', 100000, 300000, 0, '2026-05-09T21:37:00.000'),
        ((SELECT merchant_id FROM @SeedMerchants WHERE business_name = N'Alex Fashion'), N'DEMO-PL-C0043', N'Yasmin', N'Saeed', N'customer043@paylens.example.com', N'+201127529165', N'EG', N'Mansoura', N'EGP', 500000, 2000000, 0, '2026-08-26T02:26:00.000'),
        ((SELECT merchant_id FROM @SeedMerchants WHERE business_name = N'Red Sea Sports'), N'DEMO-PL-C0044', N'Ahmed', N'Ahmed', N'customer044@paylens.example.com', N'+201195889074', N'EG', N'Assiut', N'EGP', 250000, 750000, 1, '2026-04-24T01:52:00.000'),
        ((SELECT merchant_id FROM @SeedMerchants WHERE business_name = N'Delta Market'), N'DEMO-PL-C0045', N'Mahmoud', N'Morad', N'customer045@paylens.example.com', N'+201104957896', N'EG', N'Aswan', N'EGP', 1000000, 2000000, 0, '2026-09-07T06:44:00.000'),
        ((SELECT merchant_id FROM @SeedMerchants WHERE business_name = N'Cairo Home'), N'DEMO-PL-C0046', N'Fatma', N'Omar', N'customer046@paylens.example.com', N'+201017239105', N'EG', N'Tanta', N'EGP', 100000, 400000, 0, '2026-07-08T22:15:00.000'),
        ((SELECT merchant_id FROM @SeedMerchants WHERE business_name = N'Nile Electronics'), N'DEMO-PL-C0047', N'Nour', N'Adel', N'customer047@paylens.example.com', N'+201128139939', N'EG', N'Assiut', N'EGP', 100000, 300000, 1, '2026-06-02T01:05:00.000'),
        ((SELECT merchant_id FROM @SeedMerchants WHERE business_name = N'Alex Fashion'), N'DEMO-PL-C0048', N'Karim', N'Kamal', N'customer048@paylens.example.com', N'+201169614719', N'EG', N'Aswan', N'EGP', 2000000, 6000000, 0, '2026-06-27T08:38:00.000'),
        ((SELECT merchant_id FROM @SeedMerchants WHERE business_name = N'Delta Market'), N'DEMO-PL-C0049', N'Eman', N'Fouad', N'customer049@paylens.example.com', N'+201178502450', N'EG', N'Tanta', N'EGP', 50000, 100000, 0, '2026-07-22T10:03:00.000'),
        ((SELECT merchant_id FROM @SeedMerchants WHERE business_name = N'Red Sea Sports'), N'DEMO-PL-C0050', N'Asmaa', N'Mahmoud', N'customer050@paylens.example.com', N'+201517207509', N'EG', N'Cairo', N'EGP', 500000, 2000000, 0, '2026-05-06T09:32:00.000'),
        ((SELECT merchant_id FROM @SeedMerchants WHERE business_name = N'Red Sea Sports'), N'DEMO-PL-C0051', N'Abdallah', N'Omar', N'customer051@paylens.example.com', N'+201109471728', N'EG', N'Assiut', N'EGP', 50000, 150000, 0, '2026-08-15T10:52:00.000'),
        ((SELECT merchant_id FROM @SeedMerchants WHERE business_name = N'Delta Market'), N'DEMO-PL-C0052', N'Nada', N'Refaat', N'customer052@paylens.example.com', N'+201137645140', N'EG', N'Mansoura', N'EGP', 250000, 1000000, 0, '2026-04-13T19:52:00.000'),
        ((SELECT merchant_id FROM @SeedMerchants WHERE business_name = N'Red Sea Sports'), N'DEMO-PL-C0053', N'Mariam', N'Hassan', N'customer053@paylens.example.com', N'+201001186414', N'EG', N'Ismailia', N'EGP', 2000000, 6000000, 0, '2026-09-13T06:14:00.000'),
        ((SELECT merchant_id FROM @SeedMerchants WHERE business_name = N'Delta Market'), N'DEMO-PL-C0054', N'Sara', N'Ibrahim', N'customer054@paylens.example.com', N'+201242217737', N'EG', N'Mansoura', N'EGP', 250000, 1000000, 0, '2026-07-22T13:04:00.000'),
        ((SELECT merchant_id FROM @SeedMerchants WHERE business_name = N'Cairo Home'), N'DEMO-PL-C0055', N'Nour', N'Morad', N'customer055@paylens.example.com', N'+201534207286', N'EG', N'Cairo', N'EGP', 1000000, 5000000, 0, '2026-04-28T17:52:00.000'),
        ((SELECT merchant_id FROM @SeedMerchants WHERE business_name = N'Cairo Home'), N'DEMO-PL-C0056', N'Mostafa', N'Abdallah', N'customer056@paylens.example.com', N'+201269321090', N'EG', N'Aswan', N'EGP', 500000, 2500000, 0, '2026-11-01T03:41:00.000'),
        ((SELECT merchant_id FROM @SeedMerchants WHERE business_name = N'Nile Electronics'), N'DEMO-PL-C0057', N'Heba', N'Hamdy', N'customer057@paylens.example.com', N'+201126839147', N'EG', N'Cairo', N'EGP', 50000, 200000, 1, '2026-07-14T00:50:00.000'),
        ((SELECT merchant_id FROM @SeedMerchants WHERE business_name = N'Red Sea Sports'), N'DEMO-PL-C0058', N'Fatma', N'Saeed', N'customer058@paylens.example.com', N'+201084037604', N'EG', N'Alexandria', N'EGP', 250000, 500000, 1, '2026-07-31T11:24:00.000'),
        ((SELECT merchant_id FROM @SeedMerchants WHERE business_name = N'Delta Market'), N'DEMO-PL-C0059', N'Youssef', N'Saleh', N'customer059@paylens.example.com', N'+201014882167', N'EG', N'Alexandria', N'EGP', 100000, 500000, 0, '2026-10-17T22:59:00.000'),
        ((SELECT merchant_id FROM @SeedMerchants WHERE business_name = N'Delta Market'), N'DEMO-PL-C0060', N'Eman', N'Mahmoud', N'customer060@paylens.example.com', N'+201186689196', N'EG', N'Port Said', N'EGP', 100000, 200000, 0, '2026-04-15T22:18:00.000'),
        ((SELECT merchant_id FROM @SeedMerchants WHERE business_name = N'Alex Fashion'), N'DEMO-PL-C0061', N'Sara', N'Kamal', N'customer061@paylens.example.com', N'+201514937447', N'EG', N'Tanta', N'EGP', 100000, 400000, 0, '2026-07-27T13:32:00.000'),
        ((SELECT merchant_id FROM @SeedMerchants WHERE business_name = N'Cairo Home'), N'DEMO-PL-C0062', N'Yassin', N'Ahmed', N'customer062@paylens.example.com', N'+201053220476', N'EG', N'Cairo', N'EGP', 2000000, 8000000, 0, '2026-08-16T00:34:00.000'),
        ((SELECT merchant_id FROM @SeedMerchants WHERE business_name = N'Alex Fashion'), N'DEMO-PL-C0063', N'Ibrahim', N'Fouad', N'customer063@paylens.example.com', N'+201062588620', N'EG', N'Mansoura', N'EGP', 100000, 300000, 0, '2026-06-19T09:16:00.000'),
        ((SELECT merchant_id FROM @SeedMerchants WHERE business_name = N'Red Sea Sports'), N'DEMO-PL-C0064', N'Asmaa', N'Refaat', N'customer064@paylens.example.com', N'+201082294667', N'EG', N'Ismailia', N'EGP', 100000, 200000, 0, '2026-09-27T03:23:00.000'),
        ((SELECT merchant_id FROM @SeedMerchants WHERE business_name = N'Alex Fashion'), N'DEMO-PL-C0065', N'Nada', N'Kamal', N'customer065@paylens.example.com', N'+201002645619', N'EG', N'Aswan', N'EGP', 100000, 500000, 0, '2026-05-21T02:19:00.000'),
        ((SELECT merchant_id FROM @SeedMerchants WHERE business_name = N'Cairo Home'), N'DEMO-PL-C0066', N'Sara', N'Abdallah', N'customer066@paylens.example.com', N'+201023697361', N'EG', N'Mansoura', N'EGP', 100000, 400000, 0, '2026-09-22T01:12:00.000'),
        ((SELECT merchant_id FROM @SeedMerchants WHERE business_name = N'Cairo Home'), N'DEMO-PL-C0067', N'Menna', N'Mahmoud', N'customer067@paylens.example.com', N'+201593722314', N'EG', N'Giza', N'EGP', 2000000, 6000000, 0, '2026-09-28T04:11:00.000'),
        ((SELECT merchant_id FROM @SeedMerchants WHERE business_name = N'Delta Market'), N'DEMO-PL-C0068', N'Sara', N'Saeed', N'customer068@paylens.example.com', N'+201540551605', N'EG', N'Port Said', N'EGP', 500000, 2000000, 0, '2026-08-26T18:35:00.000'),
        ((SELECT merchant_id FROM @SeedMerchants WHERE business_name = N'Cairo Home'), N'DEMO-PL-C0069', N'Khaled', N'Ahmed', N'customer069@paylens.example.com', N'+201183285848', N'EG', N'Port Said', N'EGP', 1000000, 3000000, 1, '2026-05-19T00:30:00.000'),
        ((SELECT merchant_id FROM @SeedMerchants WHERE business_name = N'Red Sea Sports'), N'DEMO-PL-C0070', N'Yasmin', N'Hassan', N'customer070@paylens.example.com', N'+201597704739', N'EG', N'Cairo', N'EGP', 1000000, 5000000, 1, '2026-10-01T06:23:00.000'),
        ((SELECT merchant_id FROM @SeedMerchants WHERE business_name = N'Cairo Home'), N'DEMO-PL-C0071', N'Mohamed', N'Samir', N'customer071@paylens.example.com', N'+201204542093', N'EG', N'Giza', N'EGP', 2000000, 4000000, 0, '2026-10-01T20:12:00.000'),
        ((SELECT merchant_id FROM @SeedMerchants WHERE business_name = N'Cairo Home'), N'DEMO-PL-C0072', N'Shaimaa', N'Hassan', N'customer072@paylens.example.com', N'+201232494224', N'EG', N'Giza', N'EGP', 250000, 500000, 0, '2026-05-27T14:22:00.000'),
        ((SELECT merchant_id FROM @SeedMerchants WHERE business_name = N'Nile Electronics'), N'DEMO-PL-C0073', N'Rahma', N'Farouk', N'customer073@paylens.example.com', N'+201259821533', N'EG', N'Assiut', N'EGP', 50000, 100000, 0, '2026-08-31T04:50:00.000'),
        ((SELECT merchant_id FROM @SeedMerchants WHERE business_name = N'Red Sea Sports'), N'DEMO-PL-C0074', N'Karim', N'Hamdy', N'customer074@paylens.example.com', N'+201172801556', N'EG', N'Port Said', N'EGP', 500000, 2500000, 1, '2026-06-05T04:11:00.000'),
        ((SELECT merchant_id FROM @SeedMerchants WHERE business_name = N'Nile Electronics'), N'DEMO-PL-C0075', N'Shaimaa', N'Omar', N'customer075@paylens.example.com', N'+201031616137', N'EG', N'Port Said', N'EGP', 1000000, 3000000, 0, '2026-07-05T04:47:00.000'),
        ((SELECT merchant_id FROM @SeedMerchants WHERE business_name = N'Delta Market'), N'DEMO-PL-C0076', N'Mahmoud', N'Abdallah', N'customer076@paylens.example.com', N'+201108664255', N'EG', N'Tanta', N'EGP', 250000, 1250000, 1, '2026-09-03T09:39:00.000'),
        ((SELECT merchant_id FROM @SeedMerchants WHERE business_name = N'Cairo Home'), N'DEMO-PL-C0077', N'Salma', N'Othman', N'customer077@paylens.example.com', N'+201286806900', N'EG', N'Hurghada', N'EGP', 500000, 2000000, 0, '2026-05-02T06:32:00.000'),
        ((SELECT merchant_id FROM @SeedMerchants WHERE business_name = N'Red Sea Sports'), N'DEMO-PL-C0078', N'Nour', N'Refaat', N'customer078@paylens.example.com', N'+201136571002', N'EG', N'Ismailia', N'EGP', 250000, 1250000, 1, '2026-06-24T13:28:00.000'),
        ((SELECT merchant_id FROM @SeedMerchants WHERE business_name = N'Nile Electronics'), N'DEMO-PL-C0079', N'Ibrahim', N'Morad', N'customer079@paylens.example.com', N'+201081763688', N'EG', N'Mansoura', N'EGP', 500000, 1500000, 0, '2026-08-12T06:51:00.000'),
        ((SELECT merchant_id FROM @SeedMerchants WHERE business_name = N'Red Sea Sports'), N'DEMO-PL-C0080', N'Khaled', N'Omar', N'customer080@paylens.example.com', N'+201555350388', N'EG', N'Ismailia', N'EGP', 1000000, 3000000, 1, '2026-09-01T22:46:00.000'),
        ((SELECT merchant_id FROM @SeedMerchants WHERE business_name = N'Cairo Home'), N'DEMO-PL-C0081', N'Salma', N'Othman', N'customer081@paylens.example.com', N'+201298193299', N'EG', N'Alexandria', N'EGP', 50000, 200000, 0, '2026-07-29T14:31:00.000'),
        ((SELECT merchant_id FROM @SeedMerchants WHERE business_name = N'Delta Market'), N'DEMO-PL-C0082', N'Salma', N'Hassan', N'customer082@paylens.example.com', N'+201262146059', N'EG', N'Cairo', N'EGP', 1000000, 2000000, 0, '2026-07-30T21:49:00.000'),
        ((SELECT merchant_id FROM @SeedMerchants WHERE business_name = N'Alex Fashion'), N'DEMO-PL-C0083', N'Eman', N'Adel', N'customer083@paylens.example.com', N'+201552145889', N'EG', N'Aswan', N'EGP', 500000, 1000000, 1, '2026-06-20T05:08:00.000'),
        ((SELECT merchant_id FROM @SeedMerchants WHERE business_name = N'Alex Fashion'), N'DEMO-PL-C0084', N'Mohamed', N'Farouk', N'customer084@paylens.example.com', N'+201143520447', N'EG', N'Cairo', N'EGP', 50000, 150000, 1, '2026-06-24T19:44:00.000'),
        ((SELECT merchant_id FROM @SeedMerchants WHERE business_name = N'Delta Market'), N'DEMO-PL-C0085', N'Yassin', N'Saleh', N'customer085@paylens.example.com', N'+201244058998', N'EG', N'Assiut', N'EGP', 1000000, 4000000, 0, '2026-10-17T00:59:00.000'),
        ((SELECT merchant_id FROM @SeedMerchants WHERE business_name = N'Delta Market'), N'DEMO-PL-C0086', N'Nour', N'Hassan', N'customer086@paylens.example.com', N'+201250230286', N'EG', N'Hurghada', N'EGP', 50000, 100000, 0, '2026-05-19T19:17:00.000'),
        ((SELECT merchant_id FROM @SeedMerchants WHERE business_name = N'Delta Market'), N'DEMO-PL-C0087', N'Eman', N'Hassan', N'customer087@paylens.example.com', N'+201176203624', N'EG', N'Aswan', N'EGP', 250000, 1250000, 0, '2026-05-19T23:13:00.000'),
        ((SELECT merchant_id FROM @SeedMerchants WHERE business_name = N'Delta Market'), N'DEMO-PL-C0088', N'Nour', N'Soliman', N'customer088@paylens.example.com', N'+201246583794', N'EG', N'Cairo', N'EGP', 250000, 750000, 0, '2026-08-26T10:44:00.000'),
        ((SELECT merchant_id FROM @SeedMerchants WHERE business_name = N'Alex Fashion'), N'DEMO-PL-C0089', N'Yasmin', N'Soliman', N'customer089@paylens.example.com', N'+201206494952', N'EG', N'Giza', N'EGP', 1000000, 4000000, 0, '2026-08-10T00:32:00.000'),
        ((SELECT merchant_id FROM @SeedMerchants WHERE business_name = N'Alex Fashion'), N'DEMO-PL-C0090', N'Asmaa', N'Saleh', N'customer090@paylens.example.com', N'+201133525053', N'EG', N'Mansoura', N'EGP', 500000, 1000000, 0, '2026-07-26T00:23:00.000'),
        ((SELECT merchant_id FROM @SeedMerchants WHERE business_name = N'Delta Market'), N'DEMO-PL-C0091', N'Sara', N'Mansour', N'customer091@paylens.example.com', N'+201037985310', N'EG', N'Assiut', N'EGP', 2000000, 10000000, 1, '2026-11-06T18:00:00.000'),
        ((SELECT merchant_id FROM @SeedMerchants WHERE business_name = N'Nile Electronics'), N'DEMO-PL-C0092', N'Aya', N'Refaat', N'customer092@paylens.example.com', N'+201294278472', N'EG', N'Ismailia', N'EGP', 1000000, 4000000, 1, '2026-10-05T20:19:00.000'),
        ((SELECT merchant_id FROM @SeedMerchants WHERE business_name = N'Alex Fashion'), N'DEMO-PL-C0093', N'Nour', N'Omar', N'customer093@paylens.example.com', N'+201109881081', N'EG', N'Tanta', N'EGP', 250000, 500000, 0, '2026-05-07T05:25:00.000'),
        ((SELECT merchant_id FROM @SeedMerchants WHERE business_name = N'Delta Market'), N'DEMO-PL-C0094', N'Hassan', N'Farouk', N'customer094@paylens.example.com', N'+201111774327', N'EG', N'Alexandria', N'EGP', 50000, 100000, 0, '2026-09-14T04:14:00.000'),
        ((SELECT merchant_id FROM @SeedMerchants WHERE business_name = N'Cairo Home'), N'DEMO-PL-C0095', N'Khaled', N'Soliman', N'customer095@paylens.example.com', N'+201130781153', N'EG', N'Giza', N'EGP', 500000, 1500000, 0, '2026-06-10T20:28:00.000'),
        ((SELECT merchant_id FROM @SeedMerchants WHERE business_name = N'Red Sea Sports'), N'DEMO-PL-C0096', N'Omar', N'Soliman', N'customer096@paylens.example.com', N'+201062879818', N'EG', N'Alexandria', N'EGP', 1000000, 5000000, 0, '2026-09-27T01:22:00.000'),
        ((SELECT merchant_id FROM @SeedMerchants WHERE business_name = N'Cairo Home'), N'DEMO-PL-C0097', N'Hussein', N'Soliman', N'customer097@paylens.example.com', N'+201055364636', N'EG', N'Aswan', N'EGP', 2000000, 8000000, 1, '2026-05-31T20:31:00.000'),
        ((SELECT merchant_id FROM @SeedMerchants WHERE business_name = N'Delta Market'), N'DEMO-PL-C0098', N'Nour', N'Saeed', N'customer098@paylens.example.com', N'+201137604702', N'EG', N'Assiut', N'EGP', 250000, 750000, 0, '2026-10-18T15:16:00.000'),
        ((SELECT merchant_id FROM @SeedMerchants WHERE business_name = N'Cairo Home'), N'DEMO-PL-C0099', N'Amr', N'Othman', N'customer099@paylens.example.com', N'+201189743346', N'EG', N'Hurghada', N'EGP', 50000, 150000, 0, '2026-07-29T06:49:00.000'),
        ((SELECT merchant_id FROM @SeedMerchants WHERE business_name = N'Red Sea Sports'), N'DEMO-PL-C0100', N'Hussein', N'Kamal', N'customer100@paylens.example.com', N'+201282056047', N'EG', N'Giza', N'EGP', 1000000, 5000000, 0, '2026-06-10T12:52:00.000'),
        ((SELECT merchant_id FROM @SeedMerchants WHERE business_name = N'Delta Market'), N'DEMO-PL-C0101', N'Ali', N'Othman', N'customer101@paylens.example.com', N'+201136496941', N'EG', N'Tanta', N'EGP', 1000000, 2000000, 0, '2026-06-17T17:12:00.000'),
        ((SELECT merchant_id FROM @SeedMerchants WHERE business_name = N'Cairo Home'), N'DEMO-PL-C0102', N'Mostafa', N'Mahmoud', N'customer102@paylens.example.com', N'+201170350419', N'EG', N'Tanta', N'EGP', 500000, 2000000, 0, '2026-10-16T10:11:00.000'),
        ((SELECT merchant_id FROM @SeedMerchants WHERE business_name = N'Delta Market'), N'DEMO-PL-C0103', N'Hassan', N'Ibrahim', N'customer103@paylens.example.com', N'+201149389699', N'EG', N'Port Said', N'EGP', 100000, 300000, 0, '2026-08-10T03:40:00.000'),
        ((SELECT merchant_id FROM @SeedMerchants WHERE business_name = N'Alex Fashion'), N'DEMO-PL-C0104', N'Ahmed', N'Mahmoud', N'customer104@paylens.example.com', N'+201282544168', N'EG', N'Alexandria', N'EGP', 100000, 300000, 1, '2026-10-10T01:09:00.000'),
        ((SELECT merchant_id FROM @SeedMerchants WHERE business_name = N'Nile Electronics'), N'DEMO-PL-C0105', N'Fatma', N'Refaat', N'customer105@paylens.example.com', N'+201536538562', N'EG', N'Mansoura', N'EGP', 100000, 300000, 0, '2026-07-17T19:16:00.000'),
        ((SELECT merchant_id FROM @SeedMerchants WHERE business_name = N'Cairo Home'), N'DEMO-PL-C0106', N'Nour', N'Hassan', N'customer106@paylens.example.com', N'+201177918080', N'EG', N'Port Said', N'EGP', 50000, 250000, 0, '2026-04-26T02:26:00.000'),
        ((SELECT merchant_id FROM @SeedMerchants WHERE business_name = N'Delta Market'), N'DEMO-PL-C0107', N'Mariam', N'Kamal', N'customer107@paylens.example.com', N'+201511528152', N'EG', N'Alexandria', N'EGP', 100000, 400000, 0, '2026-09-24T12:23:00.000'),
        ((SELECT merchant_id FROM @SeedMerchants WHERE business_name = N'Cairo Home'), N'DEMO-PL-C0108', N'Dina', N'Samir', N'customer108@paylens.example.com', N'+201523684601', N'EG', N'Port Said', N'EGP', 2000000, 8000000, 1, '2026-05-13T21:22:00.000'),
        ((SELECT merchant_id FROM @SeedMerchants WHERE business_name = N'Red Sea Sports'), N'DEMO-PL-C0109', N'Amr', N'Samir', N'customer109@paylens.example.com', N'+201234955999', N'EG', N'Ismailia', N'EGP', 100000, 500000, 0, '2026-05-01T16:06:00.000'),
        ((SELECT merchant_id FROM @SeedMerchants WHERE business_name = N'Alex Fashion'), N'DEMO-PL-C0110', N'Sara', N'Adel', N'customer110@paylens.example.com', N'+201017947411', N'EG', N'Alexandria', N'EGP', 50000, 250000, 0, '2026-05-19T03:52:00.000'),
        ((SELECT merchant_id FROM @SeedMerchants WHERE business_name = N'Delta Market'), N'DEMO-PL-C0111', N'Salma', N'Mansour', N'customer111@paylens.example.com', N'+201047605542', N'EG', N'Mansoura', N'EGP', 500000, 2000000, 1, '2026-07-20T07:45:00.000'),
        ((SELECT merchant_id FROM @SeedMerchants WHERE business_name = N'Alex Fashion'), N'DEMO-PL-C0112', N'Sara', N'Samir', N'customer112@paylens.example.com', N'+201524959375', N'EG', N'Tanta', N'EGP', 50000, 150000, 0, '2026-07-05T14:04:00.000'),
        ((SELECT merchant_id FROM @SeedMerchants WHERE business_name = N'Delta Market'), N'DEMO-PL-C0113', N'Nada', N'Morad', N'customer113@paylens.example.com', N'+201047374848', N'EG', N'Alexandria', N'EGP', 2000000, 6000000, 0, '2026-09-03T11:38:00.000'),
        ((SELECT merchant_id FROM @SeedMerchants WHERE business_name = N'Delta Market'), N'DEMO-PL-C0114', N'Heba', N'Omar', N'customer114@paylens.example.com', N'+201206049151', N'EG', N'Assiut', N'EGP', 100000, 500000, 0, '2026-06-08T02:22:00.000'),
        ((SELECT merchant_id FROM @SeedMerchants WHERE business_name = N'Red Sea Sports'), N'DEMO-PL-C0115', N'Omar', N'Mahmoud', N'customer115@paylens.example.com', N'+201208987076', N'EG', N'Aswan', N'EGP', 50000, 250000, 0, '2026-04-17T22:44:00.000'),
        ((SELECT merchant_id FROM @SeedMerchants WHERE business_name = N'Alex Fashion'), N'DEMO-PL-C0116', N'Abdallah', N'Samir', N'customer116@paylens.example.com', N'+201236262716', N'EG', N'Port Said', N'EGP', 100000, 500000, 1, '2026-07-08T14:24:00.000'),
        ((SELECT merchant_id FROM @SeedMerchants WHERE business_name = N'Red Sea Sports'), N'DEMO-PL-C0117', N'Ahmed', N'Omar', N'customer117@paylens.example.com', N'+201511197844', N'EG', N'Aswan', N'EGP', 500000, 1500000, 1, '2026-10-16T04:54:00.000'),
        ((SELECT merchant_id FROM @SeedMerchants WHERE business_name = N'Red Sea Sports'), N'DEMO-PL-C0118', N'Amr', N'Fouad', N'customer118@paylens.example.com', N'+201175223962', N'EG', N'Ismailia', N'EGP', 2000000, 6000000, 0, '2026-08-20T04:46:00.000'),
        ((SELECT merchant_id FROM @SeedMerchants WHERE business_name = N'Nile Electronics'), N'DEMO-PL-C0119', N'Mostafa', N'Ibrahim', N'customer119@paylens.example.com', N'+201599573238', N'EG', N'Cairo', N'EGP', 250000, 500000, 0, '2026-05-27T02:56:00.000'),
        ((SELECT merchant_id FROM @SeedMerchants WHERE business_name = N'Nile Electronics'), N'DEMO-PL-C0120', N'Rahma', N'Kamal', N'customer120@paylens.example.com', N'+201551718359', N'EG', N'Mansoura', N'EGP', 100000, 300000, 1, '2026-05-21T17:23:00.000'),
        ((SELECT merchant_id FROM @SeedMerchants WHERE business_name = N'Alex Fashion'), N'DEMO-PL-C0121', N'Heba', N'Kamal', N'customer121@paylens.example.com', N'+201588585787', N'EG', N'Mansoura', N'EGP', 250000, 1250000, 0, '2026-05-21T15:33:00.000'),
        ((SELECT merchant_id FROM @SeedMerchants WHERE business_name = N'Nile Electronics'), N'DEMO-PL-C0122', N'Salma', N'Samir', N'customer122@paylens.example.com', N'+201511675990', N'EG', N'Tanta', N'EGP', 2000000, 10000000, 0, '2026-07-17T18:03:00.000'),
        ((SELECT merchant_id FROM @SeedMerchants WHERE business_name = N'Nile Electronics'), N'DEMO-PL-C0123', N'Amr', N'Samir', N'customer123@paylens.example.com', N'+201149129193', N'EG', N'Ismailia', N'EGP', 250000, 750000, 0, '2026-07-15T08:02:00.000'),
        ((SELECT merchant_id FROM @SeedMerchants WHERE business_name = N'Cairo Home'), N'DEMO-PL-C0124', N'Shaimaa', N'Mahmoud', N'customer124@paylens.example.com', N'+201274060475', N'EG', N'Ismailia', N'EGP', 100000, 400000, 0, '2026-08-20T20:35:00.000'),
        ((SELECT merchant_id FROM @SeedMerchants WHERE business_name = N'Cairo Home'), N'DEMO-PL-C0125', N'Hassan', N'Saeed', N'customer125@paylens.example.com', N'+201248615704', N'EG', N'Alexandria', N'EGP', 500000, 1000000, 0, '2026-10-15T05:53:00.000'),
        ((SELECT merchant_id FROM @SeedMerchants WHERE business_name = N'Alex Fashion'), N'DEMO-PL-C0126', N'Fatma', N'Mahmoud', N'customer126@paylens.example.com', N'+201017032472', N'EG', N'Assiut', N'EGP', 50000, 150000, 0, '2026-07-11T06:24:00.000'),
        ((SELECT merchant_id FROM @SeedMerchants WHERE business_name = N'Cairo Home'), N'DEMO-PL-C0127', N'Fatma', N'Mahmoud', N'customer127@paylens.example.com', N'+201066115184', N'EG', N'Ismailia', N'EGP', 2000000, 8000000, 1, '2026-08-15T15:21:00.000'),
        ((SELECT merchant_id FROM @SeedMerchants WHERE business_name = N'Nile Electronics'), N'DEMO-PL-C0128', N'Shaimaa', N'Mansour', N'customer128@paylens.example.com', N'+201038205120', N'EG', N'Aswan', N'EGP', 100000, 200000, 0, '2026-09-10T16:48:00.000'),
        ((SELECT merchant_id FROM @SeedMerchants WHERE business_name = N'Red Sea Sports'), N'DEMO-PL-C0129', N'Fatma', N'Mahmoud', N'customer129@paylens.example.com', N'+201216774291', N'EG', N'Mansoura', N'EGP', 100000, 400000, 1, '2026-07-30T03:15:00.000'),
        ((SELECT merchant_id FROM @SeedMerchants WHERE business_name = N'Red Sea Sports'), N'DEMO-PL-C0130', N'Salma', N'Omar', N'customer130@paylens.example.com', N'+201056413724', N'EG', N'Giza', N'EGP', 250000, 1250000, 0, '2026-04-13T12:19:00.000'),
        ((SELECT merchant_id FROM @SeedMerchants WHERE business_name = N'Alex Fashion'), N'DEMO-PL-C0131', N'Heba', N'Kamal', N'customer131@paylens.example.com', N'+201568985905', N'EG', N'Cairo', N'EGP', 500000, 2500000, 0, '2026-07-19T06:04:00.000'),
        ((SELECT merchant_id FROM @SeedMerchants WHERE business_name = N'Delta Market'), N'DEMO-PL-C0132', N'Dina', N'Fouad', N'customer132@paylens.example.com', N'+201204458343', N'EG', N'Assiut', N'EGP', 1000000, 4000000, 1, '2026-06-07T09:08:00.000'),
        ((SELECT merchant_id FROM @SeedMerchants WHERE business_name = N'Cairo Home'), N'DEMO-PL-C0133', N'Youssef', N'Omar', N'customer133@paylens.example.com', N'+201134014738', N'EG', N'Ismailia', N'EGP', 100000, 400000, 1, '2026-08-01T22:05:00.000'),
        ((SELECT merchant_id FROM @SeedMerchants WHERE business_name = N'Alex Fashion'), N'DEMO-PL-C0134', N'Shaimaa', N'Ahmed', N'customer134@paylens.example.com', N'+201215434207', N'EG', N'Hurghada', N'EGP', 1000000, 2000000, 0, '2026-07-16T23:57:00.000'),
        ((SELECT merchant_id FROM @SeedMerchants WHERE business_name = N'Cairo Home'), N'DEMO-PL-C0135', N'Mahmoud', N'Omar', N'customer135@paylens.example.com', N'+201006945871', N'EG', N'Giza', N'EGP', 250000, 1250000, 1, '2026-09-06T14:55:00.000'),
        ((SELECT merchant_id FROM @SeedMerchants WHERE business_name = N'Delta Market'), N'DEMO-PL-C0136', N'Mariam', N'Saleh', N'customer136@paylens.example.com', N'+201248303710', N'EG', N'Aswan', N'EGP', 1000000, 5000000, 0, '2026-04-30T15:12:00.000'),
        ((SELECT merchant_id FROM @SeedMerchants WHERE business_name = N'Red Sea Sports'), N'DEMO-PL-C0137', N'Salma', N'Refaat', N'customer137@paylens.example.com', N'+201229668492', N'EG', N'Tanta', N'EGP', 1000000, 3000000, 0, '2026-09-18T08:31:00.000'),
        ((SELECT merchant_id FROM @SeedMerchants WHERE business_name = N'Delta Market'), N'DEMO-PL-C0138', N'Youssef', N'Ahmed', N'customer138@paylens.example.com', N'+201553271591', N'EG', N'Port Said', N'EGP', 1000000, 3000000, 0, '2026-08-21T14:18:00.000'),
        ((SELECT merchant_id FROM @SeedMerchants WHERE business_name = N'Red Sea Sports'), N'DEMO-PL-C0139', N'Youssef', N'Abdallah', N'customer139@paylens.example.com', N'+201237417914', N'EG', N'Mansoura', N'EGP', 2000000, 6000000, 0, '2026-09-13T02:24:00.000'),
        ((SELECT merchant_id FROM @SeedMerchants WHERE business_name = N'Cairo Home'), N'DEMO-PL-C0140', N'Mohamed', N'Adel', N'customer140@paylens.example.com', N'+201002484059', N'EG', N'Port Said', N'EGP', 1000000, 4000000, 0, '2026-05-05T06:33:00.000'),
        ((SELECT merchant_id FROM @SeedMerchants WHERE business_name = N'Delta Market'), N'DEMO-PL-C0141', N'Rahma', N'Hassan', N'customer141@paylens.example.com', N'+201280932516', N'EG', N'Hurghada', N'EGP', 500000, 2500000, 0, '2026-08-30T19:17:00.000'),
        ((SELECT merchant_id FROM @SeedMerchants WHERE business_name = N'Nile Electronics'), N'DEMO-PL-C0142', N'Ibrahim', N'Morad', N'customer142@paylens.example.com', N'+201539460453', N'EG', N'Hurghada', N'EGP', 100000, 300000, 0, '2026-05-08T23:03:00.000'),
        ((SELECT merchant_id FROM @SeedMerchants WHERE business_name = N'Red Sea Sports'), N'DEMO-PL-C0143', N'Salma', N'Adel', N'customer143@paylens.example.com', N'+201263978175', N'EG', N'Mansoura', N'EGP', 100000, 200000, 1, '2026-09-02T03:19:00.000'),
        ((SELECT merchant_id FROM @SeedMerchants WHERE business_name = N'Alex Fashion'), N'DEMO-PL-C0144', N'Dina', N'Soliman', N'customer144@paylens.example.com', N'+201514614741', N'EG', N'Port Said', N'EGP', 100000, 300000, 0, '2026-07-10T16:20:00.000'),
        ((SELECT merchant_id FROM @SeedMerchants WHERE business_name = N'Cairo Home'), N'DEMO-PL-C0145', N'Amr', N'Morad', N'customer145@paylens.example.com', N'+201020426529', N'EG', N'Tanta', N'EGP', 50000, 100000, 1, '2026-11-05T09:59:00.000'),
        ((SELECT merchant_id FROM @SeedMerchants WHERE business_name = N'Cairo Home'), N'DEMO-PL-C0146', N'Mahmoud', N'Abdallah', N'customer146@paylens.example.com', N'+201291545494', N'EG', N'Tanta', N'EGP', 2000000, 4000000, 0, '2026-10-25T10:37:00.000'),
        ((SELECT merchant_id FROM @SeedMerchants WHERE business_name = N'Alex Fashion'), N'DEMO-PL-C0147', N'Nour', N'Othman', N'customer147@paylens.example.com', N'+201075147715', N'EG', N'Mansoura', N'EGP', 250000, 1250000, 0, '2026-09-08T09:40:00.000'),
        ((SELECT merchant_id FROM @SeedMerchants WHERE business_name = N'Red Sea Sports'), N'DEMO-PL-C0148', N'Nour', N'Othman', N'customer148@paylens.example.com', N'+201055470620', N'EG', N'Hurghada', N'EGP', 100000, 200000, 1, '2026-08-18T21:17:00.000'),
        ((SELECT merchant_id FROM @SeedMerchants WHERE business_name = N'Cairo Home'), N'DEMO-PL-C0149', N'Mohamed', N'Hassan', N'customer149@paylens.example.com', N'+201543053322', N'EG', N'Alexandria', N'EGP', 2000000, 4000000, 0, '2026-04-30T08:32:00.000'),
        ((SELECT merchant_id FROM @SeedMerchants WHERE business_name = N'Alex Fashion'), N'DEMO-PL-C0150', N'Karim', N'Saeed', N'customer150@paylens.example.com', N'+201067994399', N'EG', N'Hurghada', N'EGP', 1000000, 3000000, 1, '2026-10-14T13:03:00.000'),
        ((SELECT merchant_id FROM @SeedMerchants WHERE business_name = N'Cairo Home'), N'DEMO-PL-C0151', N'Ali', N'Ali', N'customer151@paylens.example.com', N'+201015562418', N'EG', N'Aswan', N'EGP', 100000, 300000, 0, '2026-10-29T04:31:00.000'),
        ((SELECT merchant_id FROM @SeedMerchants WHERE business_name = N'Delta Market'), N'DEMO-PL-C0152', N'Ibrahim', N'Fouad', N'customer152@paylens.example.com', N'+201109733811', N'EG', N'Hurghada', N'EGP', 50000, 100000, 0, '2026-08-28T15:19:00.000'),
        ((SELECT merchant_id FROM @SeedMerchants WHERE business_name = N'Alex Fashion'), N'DEMO-PL-C0153', N'Heba', N'Fouad', N'customer153@paylens.example.com', N'+201556197964', N'EG', N'Alexandria', N'EGP', 50000, 100000, 0, '2026-05-02T11:32:00.000'),
        ((SELECT merchant_id FROM @SeedMerchants WHERE business_name = N'Cairo Home'), N'DEMO-PL-C0154', N'Khaled', N'Omar', N'customer154@paylens.example.com', N'+201248848812', N'EG', N'Aswan', N'EGP', 2000000, 6000000, 0, '2026-10-17T06:25:00.000'),
        ((SELECT merchant_id FROM @SeedMerchants WHERE business_name = N'Cairo Home'), N'DEMO-PL-C0155', N'Rahma', N'Saeed', N'customer155@paylens.example.com', N'+201234343610', N'EG', N'Giza', N'EGP', 50000, 250000, 1, '2026-04-16T06:19:00.000'),
        ((SELECT merchant_id FROM @SeedMerchants WHERE business_name = N'Alex Fashion'), N'DEMO-PL-C0156', N'Ahmed', N'Refaat', N'customer156@paylens.example.com', N'+201230401118', N'EG', N'Mansoura', N'EGP', 250000, 500000, 0, '2026-07-22T09:51:00.000'),
        ((SELECT merchant_id FROM @SeedMerchants WHERE business_name = N'Alex Fashion'), N'DEMO-PL-C0157', N'Asmaa', N'Ali', N'customer157@paylens.example.com', N'+201122327940', N'EG', N'Aswan', N'EGP', 500000, 2000000, 1, '2026-07-25T16:40:00.000'),
        ((SELECT merchant_id FROM @SeedMerchants WHERE business_name = N'Nile Electronics'), N'DEMO-PL-C0158', N'Yassin', N'Soliman', N'customer158@paylens.example.com', N'+201209182736', N'EG', N'Alexandria', N'EGP', 250000, 1250000, 0, '2026-07-09T17:03:00.000'),
        ((SELECT merchant_id FROM @SeedMerchants WHERE business_name = N'Alex Fashion'), N'DEMO-PL-C0159', N'Dina', N'Farouk', N'customer159@paylens.example.com', N'+201009146966', N'EG', N'Ismailia', N'EGP', 50000, 150000, 0, '2026-08-12T15:03:00.000'),
        ((SELECT merchant_id FROM @SeedMerchants WHERE business_name = N'Alex Fashion'), N'DEMO-PL-C0160', N'Mariam', N'Farouk', N'customer160@paylens.example.com', N'+201297590664', N'EG', N'Mansoura', N'EGP', 50000, 200000, 0, '2026-06-27T08:08:00.000'),
        ((SELECT merchant_id FROM @SeedMerchants WHERE business_name = N'Nile Electronics'), N'DEMO-PL-C0161', N'Mariam', N'Refaat', N'customer161@paylens.example.com', N'+201078810503', N'EG', N'Aswan', N'EGP', 500000, 1000000, 0, '2026-05-10T11:27:00.000'),
        ((SELECT merchant_id FROM @SeedMerchants WHERE business_name = N'Delta Market'), N'DEMO-PL-C0162', N'Shaimaa', N'Refaat', N'customer162@paylens.example.com', N'+201194919562', N'EG', N'Cairo', N'EGP', 1000000, 4000000, 0, '2026-04-30T20:47:00.000'),
        ((SELECT merchant_id FROM @SeedMerchants WHERE business_name = N'Nile Electronics'), N'DEMO-PL-C0163', N'Menna', N'Samir', N'customer163@paylens.example.com', N'+201085989265', N'EG', N'Tanta', N'EGP', 1000000, 3000000, 0, '2026-04-27T03:36:00.000'),
        ((SELECT merchant_id FROM @SeedMerchants WHERE business_name = N'Delta Market'), N'DEMO-PL-C0164', N'Nada', N'Fouad', N'customer164@paylens.example.com', N'+201289871958', N'EG', N'Assiut', N'EGP', 1000000, 4000000, 0, '2026-07-13T14:08:00.000'),
        ((SELECT merchant_id FROM @SeedMerchants WHERE business_name = N'Alex Fashion'), N'DEMO-PL-C0165', N'Ali', N'Samir', N'customer165@paylens.example.com', N'+201239603068', N'EG', N'Alexandria', N'EGP', 50000, 200000, 0, '2026-08-16T09:25:00.000'),
        ((SELECT merchant_id FROM @SeedMerchants WHERE business_name = N'Nile Electronics'), N'DEMO-PL-C0166', N'Hassan', N'Ibrahim', N'customer166@paylens.example.com', N'+201000853425', N'EG', N'Aswan', N'EGP', 500000, 2500000, 0, '2026-08-20T19:09:00.000'),
        ((SELECT merchant_id FROM @SeedMerchants WHERE business_name = N'Alex Fashion'), N'DEMO-PL-C0167', N'Abdallah', N'Adel', N'customer167@paylens.example.com', N'+201163995981', N'EG', N'Ismailia', N'EGP', 1000000, 2000000, 0, '2026-06-12T16:02:00.000'),
        ((SELECT merchant_id FROM @SeedMerchants WHERE business_name = N'Alex Fashion'), N'DEMO-PL-C0168', N'Nada', N'Saleh', N'customer168@paylens.example.com', N'+201257159545', N'EG', N'Tanta', N'EGP', 2000000, 10000000, 0, '2026-04-15T17:20:00.000'),
        ((SELECT merchant_id FROM @SeedMerchants WHERE business_name = N'Alex Fashion'), N'DEMO-PL-C0169', N'Nada', N'Othman', N'customer169@paylens.example.com', N'+201149914156', N'EG', N'Port Said', N'EGP', 1000000, 4000000, 0, '2026-07-03T02:39:00.000'),
        ((SELECT merchant_id FROM @SeedMerchants WHERE business_name = N'Delta Market'), N'DEMO-PL-C0170', N'Amr', N'Ibrahim', N'customer170@paylens.example.com', N'+201274096033', N'EG', N'Alexandria', N'EGP', 250000, 500000, 0, '2026-07-24T08:03:00.000'),
        ((SELECT merchant_id FROM @SeedMerchants WHERE business_name = N'Cairo Home'), N'DEMO-PL-C0171', N'Eman', N'Hamdy', N'customer171@paylens.example.com', N'+201201571502', N'EG', N'Giza', N'EGP', 50000, 200000, 0, '2026-06-19T11:59:00.000'),
        ((SELECT merchant_id FROM @SeedMerchants WHERE business_name = N'Alex Fashion'), N'DEMO-PL-C0172', N'Nada', N'Hamdy', N'customer172@paylens.example.com', N'+201196835289', N'EG', N'Assiut', N'EGP', 50000, 250000, 1, '2026-05-31T05:06:00.000'),
        ((SELECT merchant_id FROM @SeedMerchants WHERE business_name = N'Red Sea Sports'), N'DEMO-PL-C0173', N'Dina', N'Hamdy', N'customer173@paylens.example.com', N'+201172051632', N'EG', N'Ismailia', N'EGP', 500000, 1500000, 0, '2026-09-18T07:57:00.000'),
        ((SELECT merchant_id FROM @SeedMerchants WHERE business_name = N'Nile Electronics'), N'DEMO-PL-C0174', N'Nour', N'Samir', N'customer174@paylens.example.com', N'+201559359152', N'EG', N'Alexandria', N'EGP', 250000, 750000, 0, '2026-08-28T17:40:00.000'),
        ((SELECT merchant_id FROM @SeedMerchants WHERE business_name = N'Delta Market'), N'DEMO-PL-C0175', N'Asmaa', N'Kamal', N'customer175@paylens.example.com', N'+201534440196', N'EG', N'Ismailia', N'EGP', 50000, 150000, 0, '2026-04-22T09:00:00.000'),
        ((SELECT merchant_id FROM @SeedMerchants WHERE business_name = N'Nile Electronics'), N'DEMO-PL-C0176', N'Nour', N'Farouk', N'customer176@paylens.example.com', N'+201042410900', N'EG', N'Tanta', N'EGP', 2000000, 10000000, 1, '2026-05-02T08:44:00.000'),
        ((SELECT merchant_id FROM @SeedMerchants WHERE business_name = N'Delta Market'), N'DEMO-PL-C0177', N'Sara', N'Hamdy', N'customer177@paylens.example.com', N'+201018444389', N'EG', N'Cairo', N'EGP', 250000, 1250000, 1, '2026-10-10T18:32:00.000'),
        ((SELECT merchant_id FROM @SeedMerchants WHERE business_name = N'Nile Electronics'), N'DEMO-PL-C0178', N'Sara', N'Othman', N'customer178@paylens.example.com', N'+201183632029', N'EG', N'Ismailia', N'EGP', 1000000, 3000000, 0, '2026-08-23T19:58:00.000'),
        ((SELECT merchant_id FROM @SeedMerchants WHERE business_name = N'Red Sea Sports'), N'DEMO-PL-C0179', N'Sara', N'Samir', N'customer179@paylens.example.com', N'+201121474597', N'EG', N'Giza', N'EGP', 100000, 500000, 0, '2026-07-11T12:28:00.000'),
        ((SELECT merchant_id FROM @SeedMerchants WHERE business_name = N'Cairo Home'), N'DEMO-PL-C0180', N'Ahmed', N'Hassan', N'customer180@paylens.example.com', N'+201280005664', N'EG', N'Alexandria', N'EGP', 250000, 500000, 0, '2026-08-20T16:02:00.000'),
        ((SELECT merchant_id FROM @SeedMerchants WHERE business_name = N'Red Sea Sports'), N'DEMO-PL-C0181', N'Nour', N'Mansour', N'customer181@paylens.example.com', N'+201049855406', N'EG', N'Mansoura', N'EGP', 500000, 1000000, 0, '2026-04-13T17:29:00.000'),
        ((SELECT merchant_id FROM @SeedMerchants WHERE business_name = N'Cairo Home'), N'DEMO-PL-C0182', N'Fatma', N'Adel', N'customer182@paylens.example.com', N'+201598676309', N'EG', N'Mansoura', N'EGP', 100000, 300000, 0, '2026-06-04T13:47:00.000'),
        ((SELECT merchant_id FROM @SeedMerchants WHERE business_name = N'Nile Electronics'), N'DEMO-PL-C0183', N'Shaimaa', N'Hamdy', N'customer183@paylens.example.com', N'+201191657945', N'EG', N'Hurghada', N'EGP', 500000, 1000000, 1, '2026-08-06T18:21:00.000'),
        ((SELECT merchant_id FROM @SeedMerchants WHERE business_name = N'Delta Market'), N'DEMO-PL-C0184', N'Khaled', N'Hassan', N'customer184@paylens.example.com', N'+201551087837', N'EG', N'Aswan', N'EGP', 100000, 400000, 0, '2026-05-21T15:24:00.000'),
        ((SELECT merchant_id FROM @SeedMerchants WHERE business_name = N'Nile Electronics'), N'DEMO-PL-C0185', N'Mostafa', N'Kamal', N'customer185@paylens.example.com', N'+201187622559', N'EG', N'Giza', N'EGP', 2000000, 4000000, 1, '2026-08-28T12:36:00.000'),
        ((SELECT merchant_id FROM @SeedMerchants WHERE business_name = N'Red Sea Sports'), N'DEMO-PL-C0186', N'Heba', N'Ibrahim', N'customer186@paylens.example.com', N'+201223002872', N'EG', N'Alexandria', N'EGP', 1000000, 4000000, 0, '2026-08-29T13:21:00.000'),
        ((SELECT merchant_id FROM @SeedMerchants WHERE business_name = N'Nile Electronics'), N'DEMO-PL-C0187', N'Yasmin', N'Fouad', N'customer187@paylens.example.com', N'+201139752403', N'EG', N'Hurghada', N'EGP', 2000000, 10000000, 0, '2026-05-09T07:12:00.000'),
        ((SELECT merchant_id FROM @SeedMerchants WHERE business_name = N'Delta Market'), N'DEMO-PL-C0188', N'Dina', N'Hamdy', N'customer188@paylens.example.com', N'+201116075113', N'EG', N'Mansoura', N'EGP', 250000, 750000, 0, '2026-10-10T20:25:00.000'),
        ((SELECT merchant_id FROM @SeedMerchants WHERE business_name = N'Cairo Home'), N'DEMO-PL-C0189', N'Yassin', N'Soliman', N'customer189@paylens.example.com', N'+201523538049', N'EG', N'Port Said', N'EGP', 1000000, 4000000, 0, '2026-05-04T14:05:00.000'),
        ((SELECT merchant_id FROM @SeedMerchants WHERE business_name = N'Delta Market'), N'DEMO-PL-C0190', N'Abdallah', N'Abdallah', N'customer190@paylens.example.com', N'+201589490814', N'EG', N'Aswan', N'EGP', 250000, 500000, 0, '2026-10-15T09:18:00.000'),
        ((SELECT merchant_id FROM @SeedMerchants WHERE business_name = N'Nile Electronics'), N'DEMO-PL-C0191', N'Ibrahim', N'Ibrahim', N'customer191@paylens.example.com', N'+201181347366', N'EG', N'Tanta', N'EGP', 100000, 200000, 0, '2026-07-19T11:18:00.000'),
        ((SELECT merchant_id FROM @SeedMerchants WHERE business_name = N'Delta Market'), N'DEMO-PL-C0192', N'Hussein', N'Refaat', N'customer192@paylens.example.com', N'+201093447482', N'EG', N'Aswan', N'EGP', 500000, 2500000, 0, '2026-10-07T00:28:00.000'),
        ((SELECT merchant_id FROM @SeedMerchants WHERE business_name = N'Cairo Home'), N'DEMO-PL-C0193', N'Omar', N'Refaat', N'customer193@paylens.example.com', N'+201220714131', N'EG', N'Cairo', N'EGP', 2000000, 6000000, 0, '2026-08-07T11:40:00.000'),
        ((SELECT merchant_id FROM @SeedMerchants WHERE business_name = N'Cairo Home'), N'DEMO-PL-C0194', N'Abdallah', N'Samir', N'customer194@paylens.example.com', N'+201204344128', N'EG', N'Hurghada', N'EGP', 50000, 100000, 0, '2026-05-16T17:51:00.000'),
        ((SELECT merchant_id FROM @SeedMerchants WHERE business_name = N'Nile Electronics'), N'DEMO-PL-C0195', N'Eman', N'Fouad', N'customer195@paylens.example.com', N'+201126443813', N'EG', N'Hurghada', N'EGP', 1000000, 3000000, 0, '2026-06-26T22:13:00.000'),
        ((SELECT merchant_id FROM @SeedMerchants WHERE business_name = N'Cairo Home'), N'DEMO-PL-C0196', N'Heba', N'Mansour', N'customer196@paylens.example.com', N'+201588624838', N'EG', N'Alexandria', N'EGP', 500000, 2000000, 0, '2026-10-08T15:59:00.000'),
        ((SELECT merchant_id FROM @SeedMerchants WHERE business_name = N'Delta Market'), N'DEMO-PL-C0197', N'Khaled', N'Adel', N'customer197@paylens.example.com', N'+201290504788', N'EG', N'Cairo', N'EGP', 50000, 100000, 1, '2026-10-07T01:38:00.000'),
        ((SELECT merchant_id FROM @SeedMerchants WHERE business_name = N'Cairo Home'), N'DEMO-PL-C0198', N'Khaled', N'Hassan', N'customer198@paylens.example.com', N'+201216406470', N'EG', N'Alexandria', N'EGP', 500000, 1000000, 1, '2026-05-16T06:39:00.000'),
        ((SELECT merchant_id FROM @SeedMerchants WHERE business_name = N'Delta Market'), N'DEMO-PL-C0199', N'Rahma', N'Soliman', N'customer199@paylens.example.com', N'+201071945673', N'EG', N'Alexandria', N'EGP', 250000, 750000, 0, '2026-09-29T20:35:00.000'),
        ((SELECT merchant_id FROM @SeedMerchants WHERE business_name = N'Red Sea Sports'), N'DEMO-PL-C0200', N'Eman', N'Samir', N'customer200@paylens.example.com', N'+201165595681', N'EG', N'Cairo', N'EGP', 2000000, 10000000, 0, '2026-07-26T12:34:00.000');

    -- 3. Payment methods: one or two per customer; tokens are fictional.
    INSERT INTO dbo.customer_payment_methods (
        customer_id, processor_code, processor_account_reference, payment_token, card_brand, card_last4, is_active, created_at
    )
    OUTPUT inserted.payment_method_id INTO @SeedMethods (payment_method_id)
    VALUES
        ((SELECT customer_id FROM @SeedCustomers WHERE customer_reference = N'DEMO-PL-C0001'), N'PROC_A', N'acct_test_proc_a_m04', N'tok_test_pl_3cc477b6abe8f044c536bda198f44d86', N'visa', N'0721', 1, '2026-07-19T22:26:00.000'),
        ((SELECT customer_id FROM @SeedCustomers WHERE customer_reference = N'DEMO-PL-C0001'), N'PROC_A', N'acct_test_proc_a_m04', N'tok_test_pl_3b2766547116a4caec19dde4b485d27b', N'mastercard', N'0019', 0, '2026-07-21T02:26:00.000'),
        ((SELECT customer_id FROM @SeedCustomers WHERE customer_reference = N'DEMO-PL-C0002'), N'PROC_A', N'acct_test_proc_a_m05', N'tok_test_pl_caa0414fc1d4b26b68d935818a34193d', N'visa', N'1410', 1, '2026-09-15T15:00:00.000'),
        ((SELECT customer_id FROM @SeedCustomers WHERE customer_reference = N'DEMO-PL-C0003'), N'PROC_A', N'acct_test_proc_a_m01', N'tok_test_pl_781d90a2025c9809b50e181c0f3241f6', N'mastercard', N'0830', 1, '2026-05-06T20:09:00.000'),
        ((SELECT customer_id FROM @SeedCustomers WHERE customer_reference = N'DEMO-PL-C0004'), N'PROC_A', N'acct_test_proc_a_m05', N'tok_test_pl_ba9ecf3650fe539b6fce0f9f8861ed2c', N'visa', N'6176', 1, '2026-04-18T08:21:00.000'),
        ((SELECT customer_id FROM @SeedCustomers WHERE customer_reference = N'DEMO-PL-C0005'), N'PROC_A', N'acct_test_proc_a_m03', N'tok_test_pl_a3fb168781aac21c06b00e061c5a43d4', N'mastercard', N'5085', 1, '2026-04-18T05:22:00.000'),
        ((SELECT customer_id FROM @SeedCustomers WHERE customer_reference = N'DEMO-PL-C0005'), N'PROC_A', N'acct_test_proc_a_m03', N'tok_test_pl_91e4b1f381a04bbf2924dd468d32c028', N'visa', N'3986', 0, '2026-04-17T03:22:00.000'),
        ((SELECT customer_id FROM @SeedCustomers WHERE customer_reference = N'DEMO-PL-C0006'), N'PROC_A', N'acct_test_proc_a_m01', N'tok_test_pl_6cb5c0dbb2d077fdac6b522c8a91d773', N'mastercard', N'8242', 1, '2026-08-12T15:08:00.000'),
        ((SELECT customer_id FROM @SeedCustomers WHERE customer_reference = N'DEMO-PL-C0006'), N'PROC_A', N'acct_test_proc_a_m01', N'tok_test_pl_e0816775ea9eb05ac09a5b889566b3f0', N'mastercard', N'6512', 1, '2026-08-10T02:08:00.000'),
        ((SELECT customer_id FROM @SeedCustomers WHERE customer_reference = N'DEMO-PL-C0007'), N'PROC_A', N'acct_test_proc_a_m02', N'tok_test_pl_bfd1d852a43637d49aec7698c0ea4f8f', N'visa', N'1248', 1, '2026-08-13T03:27:00.000'),
        ((SELECT customer_id FROM @SeedCustomers WHERE customer_reference = N'DEMO-PL-C0008'), N'PROC_A', N'acct_test_proc_a_m05', N'tok_test_pl_c1285de3a060f70c0b90d498450993bf', N'visa', N'6471', 1, '2026-08-04T05:36:00.000'),
        ((SELECT customer_id FROM @SeedCustomers WHERE customer_reference = N'DEMO-PL-C0009'), N'PROC_A', N'acct_test_proc_a_m03', N'tok_test_pl_57516cbd30bfac6ad0f9bc264d408770', N'mastercard', N'3694', 1, '2026-10-31T11:22:00.000'),
        ((SELECT customer_id FROM @SeedCustomers WHERE customer_reference = N'DEMO-PL-C0010'), N'PROC_A', N'acct_test_proc_a_m04', N'tok_test_pl_baf63836e026bb4ff829416d1236d85a', N'mastercard', N'6223', 1, '2026-08-25T01:18:00.000'),
        ((SELECT customer_id FROM @SeedCustomers WHERE customer_reference = N'DEMO-PL-C0011'), N'PROC_A', N'acct_test_proc_a_m05', N'tok_test_pl_f4518e702ce8581c37c5fda8b2abcf99', N'mastercard', N'6108', 1, '2026-07-02T19:16:00.000'),
        ((SELECT customer_id FROM @SeedCustomers WHERE customer_reference = N'DEMO-PL-C0012'), N'PROC_A', N'acct_test_proc_a_m01', N'tok_test_pl_db4e21ebc73879b4e6556d453a7c2ce2', N'mastercard', N'7903', 1, '2026-06-03T12:51:00.000'),
        ((SELECT customer_id FROM @SeedCustomers WHERE customer_reference = N'DEMO-PL-C0012'), N'PROC_A', N'acct_test_proc_a_m01', N'tok_test_pl_35622b751b8dc7aa8d78d98efe6d7862', N'mastercard', N'8868', 1, '2026-06-06T12:51:00.000'),
        ((SELECT customer_id FROM @SeedCustomers WHERE customer_reference = N'DEMO-PL-C0013'), N'PROC_A', N'acct_test_proc_a_m03', N'tok_test_pl_c709be9a86d5685b53ef49d801892931', N'mastercard', N'7803', 1, '2026-10-16T13:10:00.000'),
        ((SELECT customer_id FROM @SeedCustomers WHERE customer_reference = N'DEMO-PL-C0013'), N'PROC_A', N'acct_test_proc_a_m03', N'tok_test_pl_469097e25beffc2c6f081376bee9aa45', N'visa', N'9410', 1, '2026-10-14T01:10:00.000'),
        ((SELECT customer_id FROM @SeedCustomers WHERE customer_reference = N'DEMO-PL-C0014'), N'PROC_A', N'acct_test_proc_a_m05', N'tok_test_pl_bde3d9b96588a50a80d90d98d920b081', N'mastercard', N'4847', 1, '2026-06-06T13:33:00.000'),
        ((SELECT customer_id FROM @SeedCustomers WHERE customer_reference = N'DEMO-PL-C0014'), N'PROC_A', N'acct_test_proc_a_m05', N'tok_test_pl_5e3d3d3b6fbe707abc38b440ab5ce00f', N'mastercard', N'6309', 0, '2026-06-08T03:33:00.000'),
        ((SELECT customer_id FROM @SeedCustomers WHERE customer_reference = N'DEMO-PL-C0015'), N'PROC_A', N'acct_test_proc_a_m01', N'tok_test_pl_7d402f7370c71837f3ec6c19f927b6d8', N'visa', N'8756', 1, '2026-09-17T17:33:00.000'),
        ((SELECT customer_id FROM @SeedCustomers WHERE customer_reference = N'DEMO-PL-C0015'), N'PROC_A', N'acct_test_proc_a_m01', N'tok_test_pl_81b159ff541cabf4c202fec648ec20f7', N'mastercard', N'4069', 1, '2026-09-15T12:33:00.000'),
        ((SELECT customer_id FROM @SeedCustomers WHERE customer_reference = N'DEMO-PL-C0016'), N'PROC_A', N'acct_test_proc_a_m01', N'tok_test_pl_ba24af7d38ff37a1de4a4aa9d0c72bba', N'visa', N'4793', 1, '2026-08-02T01:50:00.000'),
        ((SELECT customer_id FROM @SeedCustomers WHERE customer_reference = N'DEMO-PL-C0016'), N'PROC_A', N'acct_test_proc_a_m01', N'tok_test_pl_772298619d131a08615130c0670a5c27', N'visa', N'7326', 1, '2026-08-01T05:50:00.000'),
        ((SELECT customer_id FROM @SeedCustomers WHERE customer_reference = N'DEMO-PL-C0017'), N'PROC_A', N'acct_test_proc_a_m03', N'tok_test_pl_0bd4cb9982268aab8e8529eddf5bd28c', N'visa', N'4108', 1, '2026-09-18T20:56:00.000'),
        ((SELECT customer_id FROM @SeedCustomers WHERE customer_reference = N'DEMO-PL-C0018'), N'PROC_A', N'acct_test_proc_a_m05', N'tok_test_pl_5e2d21aa7a237f18e9bc10fd2991bb88', N'mastercard', N'4299', 1, '2026-10-25T14:33:00.000'),
        ((SELECT customer_id FROM @SeedCustomers WHERE customer_reference = N'DEMO-PL-C0019'), N'PROC_A', N'acct_test_proc_a_m01', N'tok_test_pl_b21f94c66eb0a3f65a06c596e82e75b7', N'visa', N'0522', 1, '2026-10-21T00:31:00.000'),
        ((SELECT customer_id FROM @SeedCustomers WHERE customer_reference = N'DEMO-PL-C0020'), N'PROC_A', N'acct_test_proc_a_m04', N'tok_test_pl_d7ccd42827bd65a7a89ba44d05512023', N'mastercard', N'3489', 1, '2026-09-14T19:07:00.000'),
        ((SELECT customer_id FROM @SeedCustomers WHERE customer_reference = N'DEMO-PL-C0020'), N'PROC_A', N'acct_test_proc_a_m04', N'tok_test_pl_f70d0e4af5a95dd266a4990a70815781', N'mastercard', N'8517', 1, '2026-09-14T17:07:00.000'),
        ((SELECT customer_id FROM @SeedCustomers WHERE customer_reference = N'DEMO-PL-C0021'), N'PROC_A', N'acct_test_proc_a_m05', N'tok_test_pl_405d6616191138072aa5d012fd679c9b', N'mastercard', N'1298', 1, '2026-06-27T05:02:00.000'),
        ((SELECT customer_id FROM @SeedCustomers WHERE customer_reference = N'DEMO-PL-C0022'), N'PROC_A', N'acct_test_proc_a_m05', N'tok_test_pl_c55d57cdab0959cb922578ead5448f18', N'visa', N'4053', 1, '2026-10-28T04:16:00.000'),
        ((SELECT customer_id FROM @SeedCustomers WHERE customer_reference = N'DEMO-PL-C0023'), N'PROC_A', N'acct_test_proc_a_m03', N'tok_test_pl_90e617eb39e583b10e1fd740c886264a', N'visa', N'0639', 1, '2026-06-08T08:42:00.000'),
        ((SELECT customer_id FROM @SeedCustomers WHERE customer_reference = N'DEMO-PL-C0024'), N'PROC_A', N'acct_test_proc_a_m01', N'tok_test_pl_110aec7b74805f5bd78e7454ccda5a28', N'mastercard', N'0292', 1, '2026-06-15T15:26:00.000'),
        ((SELECT customer_id FROM @SeedCustomers WHERE customer_reference = N'DEMO-PL-C0024'), N'PROC_A', N'acct_test_proc_a_m01', N'tok_test_pl_79797eccec3d37804736ea707437d02e', N'mastercard', N'9261', 0, '2026-06-16T09:26:00.000'),
        ((SELECT customer_id FROM @SeedCustomers WHERE customer_reference = N'DEMO-PL-C0025'), N'PROC_A', N'acct_test_proc_a_m03', N'tok_test_pl_05276a756e4a45a535250068340db947', N'visa', N'3344', 1, '2026-06-23T18:09:00.000'),
        ((SELECT customer_id FROM @SeedCustomers WHERE customer_reference = N'DEMO-PL-C0025'), N'PROC_A', N'acct_test_proc_a_m03', N'tok_test_pl_1a683294d2f1e424f81d99df03529814', N'mastercard', N'5954', 1, '2026-06-23T13:09:00.000'),
        ((SELECT customer_id FROM @SeedCustomers WHERE customer_reference = N'DEMO-PL-C0026'), N'PROC_A', N'acct_test_proc_a_m03', N'tok_test_pl_a063f2035537f763ab835b810bd6a989', N'mastercard', N'2273', 1, '2026-08-09T01:16:00.000'),
        ((SELECT customer_id FROM @SeedCustomers WHERE customer_reference = N'DEMO-PL-C0027'), N'PROC_A', N'acct_test_proc_a_m01', N'tok_test_pl_f9f1f5084c5a270073531a8fe3fee74e', N'visa', N'1876', 1, '2026-10-10T00:50:00.000'),
        ((SELECT customer_id FROM @SeedCustomers WHERE customer_reference = N'DEMO-PL-C0028'), N'PROC_A', N'acct_test_proc_a_m04', N'tok_test_pl_c4f6c50fe9bfe642f1b0f074bb5968d4', N'visa', N'6750', 1, '2026-07-28T12:26:00.000'),
        ((SELECT customer_id FROM @SeedCustomers WHERE customer_reference = N'DEMO-PL-C0029'), N'PROC_A', N'acct_test_proc_a_m02', N'tok_test_pl_ae3d03b7950c9d47f9c430516c2fb21f', N'visa', N'4824', 1, '2026-07-17T08:22:00.000'),
        ((SELECT customer_id FROM @SeedCustomers WHERE customer_reference = N'DEMO-PL-C0029'), N'PROC_A', N'acct_test_proc_a_m02', N'tok_test_pl_523a9424c68c68c8208e692cb70462ba', N'visa', N'6066', 0, '2026-07-16T21:22:00.000'),
        ((SELECT customer_id FROM @SeedCustomers WHERE customer_reference = N'DEMO-PL-C0030'), N'PROC_A', N'acct_test_proc_a_m03', N'tok_test_pl_ee40246701ca3b7a946aa9e662d8e734', N'mastercard', N'3948', 1, '2026-06-06T04:56:00.000'),
        ((SELECT customer_id FROM @SeedCustomers WHERE customer_reference = N'DEMO-PL-C0031'), N'PROC_A', N'acct_test_proc_a_m03', N'tok_test_pl_88e2c5cbd17da21f73bca7135309e54d', N'mastercard', N'6867', 1, '2026-05-29T08:14:00.000'),
        ((SELECT customer_id FROM @SeedCustomers WHERE customer_reference = N'DEMO-PL-C0031'), N'PROC_A', N'acct_test_proc_a_m03', N'tok_test_pl_def4536755dacbec4e1a55953027e458', N'visa', N'8919', 1, '2026-05-28T22:14:00.000'),
        ((SELECT customer_id FROM @SeedCustomers WHERE customer_reference = N'DEMO-PL-C0032'), N'PROC_A', N'acct_test_proc_a_m02', N'tok_test_pl_036494a730c3d15d96032d1de1ed3dbe', N'visa', N'2738', 1, '2026-05-09T00:08:00.000'),
        ((SELECT customer_id FROM @SeedCustomers WHERE customer_reference = N'DEMO-PL-C0033'), N'PROC_A', N'acct_test_proc_a_m05', N'tok_test_pl_ad617aa28905a2f5134a71b69ad3220e', N'mastercard', N'1116', 1, '2026-06-30T02:13:00.000'),
        ((SELECT customer_id FROM @SeedCustomers WHERE customer_reference = N'DEMO-PL-C0033'), N'PROC_A', N'acct_test_proc_a_m05', N'tok_test_pl_3b1b487e4c3b24fe4cdab78dbf7d1fec', N'mastercard', N'7855', 1, '2026-06-28T22:13:00.000'),
        ((SELECT customer_id FROM @SeedCustomers WHERE customer_reference = N'DEMO-PL-C0034'), N'PROC_A', N'acct_test_proc_a_m01', N'tok_test_pl_7a951b797dda599a19854acc74488ced', N'visa', N'1521', 1, '2026-09-06T07:08:00.000'),
        ((SELECT customer_id FROM @SeedCustomers WHERE customer_reference = N'DEMO-PL-C0035'), N'PROC_A', N'acct_test_proc_a_m05', N'tok_test_pl_071ea97502cdafc58da710f8e34a8ddb', N'visa', N'4903', 1, '2026-05-10T21:53:00.000'),
        ((SELECT customer_id FROM @SeedCustomers WHERE customer_reference = N'DEMO-PL-C0035'), N'PROC_A', N'acct_test_proc_a_m05', N'tok_test_pl_d7bac28f9eafb9aa437ff58d991bf735', N'visa', N'6305', 0, '2026-05-12T05:53:00.000'),
        ((SELECT customer_id FROM @SeedCustomers WHERE customer_reference = N'DEMO-PL-C0036'), N'PROC_A', N'acct_test_proc_a_m04', N'tok_test_pl_0565ce41bcaeb6d5cdbf331354999c90', N'mastercard', N'8377', 1, '2026-05-12T08:48:00.000'),
        ((SELECT customer_id FROM @SeedCustomers WHERE customer_reference = N'DEMO-PL-C0037'), N'PROC_A', N'acct_test_proc_a_m02', N'tok_test_pl_e942b601164112f21df76a1fbf0d960e', N'mastercard', N'9157', 1, '2026-07-13T00:11:00.000'),
        ((SELECT customer_id FROM @SeedCustomers WHERE customer_reference = N'DEMO-PL-C0037'), N'PROC_A', N'acct_test_proc_a_m02', N'tok_test_pl_abb611a862e941c898073f372ccb9943', N'mastercard', N'4366', 1, '2026-07-12T16:11:00.000'),
        ((SELECT customer_id FROM @SeedCustomers WHERE customer_reference = N'DEMO-PL-C0038'), N'PROC_A', N'acct_test_proc_a_m05', N'tok_test_pl_468f209c6e6bac0b852847a5d0f2a034', N'visa', N'2700', 1, '2026-04-16T10:34:00.000'),
        ((SELECT customer_id FROM @SeedCustomers WHERE customer_reference = N'DEMO-PL-C0038'), N'PROC_A', N'acct_test_proc_a_m05', N'tok_test_pl_5392b2dbe7bdc9c2cd1d1b81676ecd12', N'mastercard', N'0046', 0, '2026-04-15T22:34:00.000'),
        ((SELECT customer_id FROM @SeedCustomers WHERE customer_reference = N'DEMO-PL-C0039'), N'PROC_A', N'acct_test_proc_a_m05', N'tok_test_pl_138f0dbb438d01eaa92154e364e3d448', N'mastercard', N'7288', 1, '2026-09-25T21:28:00.000'),
        ((SELECT customer_id FROM @SeedCustomers WHERE customer_reference = N'DEMO-PL-C0040'), N'PROC_A', N'acct_test_proc_a_m05', N'tok_test_pl_9b6dcc62a534813f47b8042f23f652bc', N'visa', N'0430', 1, '2026-07-21T09:50:00.000'),
        ((SELECT customer_id FROM @SeedCustomers WHERE customer_reference = N'DEMO-PL-C0040'), N'PROC_A', N'acct_test_proc_a_m05', N'tok_test_pl_7a1871ee101830f2f9b6c44cd0edd02c', N'mastercard', N'4988', 1, '2026-07-20T04:50:00.000'),
        ((SELECT customer_id FROM @SeedCustomers WHERE customer_reference = N'DEMO-PL-C0041'), N'PROC_A', N'acct_test_proc_a_m01', N'tok_test_pl_3da46a1724ff31efa4f158aff3de22de', N'visa', N'3046', 1, '2026-10-21T09:04:00.000'),
        ((SELECT customer_id FROM @SeedCustomers WHERE customer_reference = N'DEMO-PL-C0042'), N'PROC_A', N'acct_test_proc_a_m05', N'tok_test_pl_b34ef5ea2040d8b5b1229f8a66a3fb3f', N'visa', N'5095', 1, '2026-05-10T04:37:00.000'),
        ((SELECT customer_id FROM @SeedCustomers WHERE customer_reference = N'DEMO-PL-C0043'), N'PROC_A', N'acct_test_proc_a_m02', N'tok_test_pl_e28eaaf2251bff7127d48d843161fb98', N'visa', N'8526', 1, '2026-08-27T12:26:00.000'),
        ((SELECT customer_id FROM @SeedCustomers WHERE customer_reference = N'DEMO-PL-C0043'), N'PROC_A', N'acct_test_proc_a_m02', N'tok_test_pl_6393435d8a9f77dd066d600ab4cf8e12', N'visa', N'5422', 0, '2026-08-28T08:26:00.000'),
        ((SELECT customer_id FROM @SeedCustomers WHERE customer_reference = N'DEMO-PL-C0044'), N'PROC_A', N'acct_test_proc_a_m05', N'tok_test_pl_c0fccbc93da7740ac33b624c09c42497', N'mastercard', N'0731', 1, '2026-04-24T23:52:00.000'),
        ((SELECT customer_id FROM @SeedCustomers WHERE customer_reference = N'DEMO-PL-C0045'), N'PROC_A', N'acct_test_proc_a_m03', N'tok_test_pl_88a905bf2e229fe2ac404de9f517aa04', N'mastercard', N'6258', 1, '2026-09-10T01:44:00.000'),
        ((SELECT customer_id FROM @SeedCustomers WHERE customer_reference = N'DEMO-PL-C0046'), N'PROC_A', N'acct_test_proc_a_m04', N'tok_test_pl_32eaf83b440561837cc668d4d4bfb7ec', N'visa', N'6230', 1, '2026-07-09T20:15:00.000'),
        ((SELECT customer_id FROM @SeedCustomers WHERE customer_reference = N'DEMO-PL-C0046'), N'PROC_A', N'acct_test_proc_a_m04', N'tok_test_pl_01e3adf9f718b2876e0408482c64bcdb', N'visa', N'7200', 0, '2026-07-11T18:15:00.000'),
        ((SELECT customer_id FROM @SeedCustomers WHERE customer_reference = N'DEMO-PL-C0047'), N'PROC_A', N'acct_test_proc_a_m01', N'tok_test_pl_6b7f2e4def9a94988c6cacc60a98a3ab', N'mastercard', N'6655', 1, '2026-06-03T16:05:00.000'),
        ((SELECT customer_id FROM @SeedCustomers WHERE customer_reference = N'DEMO-PL-C0048'), N'PROC_A', N'acct_test_proc_a_m02', N'tok_test_pl_edb2a1e67c28d14574f7a5afceff9ef2', N'mastercard', N'6576', 1, '2026-06-28T01:38:00.000'),
        ((SELECT customer_id FROM @SeedCustomers WHERE customer_reference = N'DEMO-PL-C0049'), N'PROC_A', N'acct_test_proc_a_m03', N'tok_test_pl_f09669f5720b1d462a0f0eaeefd10c35', N'visa', N'4616', 1, '2026-07-23T00:03:00.000'),
        ((SELECT customer_id FROM @SeedCustomers WHERE customer_reference = N'DEMO-PL-C0050'), N'PROC_A', N'acct_test_proc_a_m05', N'tok_test_pl_93a54bd39b8ac0d33ca6810f1a8e727e', N'visa', N'1446', 1, '2026-05-07T06:32:00.000'),
        ((SELECT customer_id FROM @SeedCustomers WHERE customer_reference = N'DEMO-PL-C0051'), N'PROC_A', N'acct_test_proc_a_m05', N'tok_test_pl_c5af305441543dd7f364e141ff3baa21', N'mastercard', N'2637', 1, '2026-08-18T01:52:00.000'),
        ((SELECT customer_id FROM @SeedCustomers WHERE customer_reference = N'DEMO-PL-C0052'), N'PROC_A', N'acct_test_proc_a_m03', N'tok_test_pl_591d384cb23a1e22b18301e7be752e19', N'visa', N'6362', 1, '2026-04-15T21:52:00.000'),
        ((SELECT customer_id FROM @SeedCustomers WHERE customer_reference = N'DEMO-PL-C0053'), N'PROC_A', N'acct_test_proc_a_m05', N'tok_test_pl_b17ce21448ade2107f1e1a3f92fe7ecf', N'visa', N'6808', 1, '2026-09-14T23:14:00.000'),
        ((SELECT customer_id FROM @SeedCustomers WHERE customer_reference = N'DEMO-PL-C0053'), N'PROC_A', N'acct_test_proc_a_m05', N'tok_test_pl_95595420212ae6460630a2d1e065424b', N'mastercard', N'4038', 1, '2026-09-15T01:14:00.000'),
        ((SELECT customer_id FROM @SeedCustomers WHERE customer_reference = N'DEMO-PL-C0054'), N'PROC_A', N'acct_test_proc_a_m03', N'tok_test_pl_4ee38773b2c1ccbe821ecbcd1d631040', N'mastercard', N'0589', 1, '2026-07-24T22:04:00.000'),
        ((SELECT customer_id FROM @SeedCustomers WHERE customer_reference = N'DEMO-PL-C0055'), N'PROC_A', N'acct_test_proc_a_m04', N'tok_test_pl_c698e846fe4ae5b74d6470aab2ce01cb', N'visa', N'5075', 1, '2026-04-28T17:52:00.000'),
        ((SELECT customer_id FROM @SeedCustomers WHERE customer_reference = N'DEMO-PL-C0056'), N'PROC_A', N'acct_test_proc_a_m04', N'tok_test_pl_81235ea59d17520b27aee9175cfd8f62', N'mastercard', N'8925', 1, '2026-11-03T02:41:00.000'),
        ((SELECT customer_id FROM @SeedCustomers WHERE customer_reference = N'DEMO-PL-C0056'), N'PROC_A', N'acct_test_proc_a_m04', N'tok_test_pl_bdb7b6b32234f65af7aab9ed4f8716cc', N'visa', N'5696', 0, '2026-11-04T00:41:00.000'),
        ((SELECT customer_id FROM @SeedCustomers WHERE customer_reference = N'DEMO-PL-C0057'), N'PROC_A', N'acct_test_proc_a_m01', N'tok_test_pl_de88ec520af38ea13a5beff754e3b7e1', N'visa', N'5028', 1, '2026-07-16T02:50:00.000'),
        ((SELECT customer_id FROM @SeedCustomers WHERE customer_reference = N'DEMO-PL-C0058'), N'PROC_A', N'acct_test_proc_a_m05', N'tok_test_pl_c16e79d2c69e29055345a17c7f4f811d', N'visa', N'9146', 1, '2026-08-01T18:24:00.000'),
        ((SELECT customer_id FROM @SeedCustomers WHERE customer_reference = N'DEMO-PL-C0059'), N'PROC_A', N'acct_test_proc_a_m03', N'tok_test_pl_0f09ad0518b6671c5d30ddd9bea872b3', N'visa', N'5407', 1, '2026-10-19T07:59:00.000'),
        ((SELECT customer_id FROM @SeedCustomers WHERE customer_reference = N'DEMO-PL-C0060'), N'PROC_A', N'acct_test_proc_a_m03', N'tok_test_pl_7c6593f1c5cdb3247071e1de1547c2fb', N'visa', N'8485', 1, '2026-04-16T21:18:00.000'),
        ((SELECT customer_id FROM @SeedCustomers WHERE customer_reference = N'DEMO-PL-C0060'), N'PROC_A', N'acct_test_proc_a_m03', N'tok_test_pl_24f663dc4e81f30fac0e118aa27ac139', N'mastercard', N'2359', 1, '2026-04-16T08:18:00.000'),
        ((SELECT customer_id FROM @SeedCustomers WHERE customer_reference = N'DEMO-PL-C0061'), N'PROC_A', N'acct_test_proc_a_m02', N'tok_test_pl_e42aa622d97105050342efc61df16167', N'mastercard', N'8758', 1, '2026-07-28T14:32:00.000'),
        ((SELECT customer_id FROM @SeedCustomers WHERE customer_reference = N'DEMO-PL-C0062'), N'PROC_A', N'acct_test_proc_a_m04', N'tok_test_pl_db8dede235e5d029be5d9b7a86ec5e3c', N'visa', N'8613', 1, '2026-08-18T04:34:00.000'),
        ((SELECT customer_id FROM @SeedCustomers WHERE customer_reference = N'DEMO-PL-C0063'), N'PROC_A', N'acct_test_proc_a_m02', N'tok_test_pl_491494f386a485e3b8b305b65c35cae4', N'visa', N'7021', 1, '2026-06-19T15:16:00.000'),
        ((SELECT customer_id FROM @SeedCustomers WHERE customer_reference = N'DEMO-PL-C0063'), N'PROC_A', N'acct_test_proc_a_m02', N'tok_test_pl_5ad387aacb14827df2292beefc49ffb1', N'visa', N'9796', 0, '2026-06-22T06:16:00.000'),
        ((SELECT customer_id FROM @SeedCustomers WHERE customer_reference = N'DEMO-PL-C0064'), N'PROC_A', N'acct_test_proc_a_m05', N'tok_test_pl_b31f2863b82cf6dfbbb40d373ea821de', N'mastercard', N'2563', 1, '2026-09-29T16:23:00.000'),
        ((SELECT customer_id FROM @SeedCustomers WHERE customer_reference = N'DEMO-PL-C0065'), N'PROC_A', N'acct_test_proc_a_m02', N'tok_test_pl_46ff7e0399bdb7cb3bcb1cc3c328635b', N'visa', N'7860', 1, '2026-05-21T11:19:00.000'),
        ((SELECT customer_id FROM @SeedCustomers WHERE customer_reference = N'DEMO-PL-C0066'), N'PROC_A', N'acct_test_proc_a_m04', N'tok_test_pl_ef352b767078031ea23d64807b26bb79', N'mastercard', N'3327', 1, '2026-09-22T18:12:00.000'),
        ((SELECT customer_id FROM @SeedCustomers WHERE customer_reference = N'DEMO-PL-C0067'), N'PROC_A', N'acct_test_proc_a_m04', N'tok_test_pl_d74aa1f7481f70590019da890ea591ab', N'visa', N'9011', 1, '2026-09-28T04:11:00.000'),
        ((SELECT customer_id FROM @SeedCustomers WHERE customer_reference = N'DEMO-PL-C0068'), N'PROC_A', N'acct_test_proc_a_m03', N'tok_test_pl_653ebda0f45d1cee40c7bc8267d6b880', N'visa', N'3720', 1, '2026-08-29T09:35:00.000'),
        ((SELECT customer_id FROM @SeedCustomers WHERE customer_reference = N'DEMO-PL-C0068'), N'PROC_A', N'acct_test_proc_a_m03', N'tok_test_pl_398c3d5b15248879f34b4fd72e85837c', N'mastercard', N'6686', 1, '2026-08-28T00:35:00.000'),
        ((SELECT customer_id FROM @SeedCustomers WHERE customer_reference = N'DEMO-PL-C0069'), N'PROC_A', N'acct_test_proc_a_m04', N'tok_test_pl_b089f712a8d594aedc858027e6fbf031', N'mastercard', N'6602', 1, '2026-05-20T02:30:00.000'),
        ((SELECT customer_id FROM @SeedCustomers WHERE customer_reference = N'DEMO-PL-C0069'), N'PROC_A', N'acct_test_proc_a_m04', N'tok_test_pl_93af8a7406be48c10523ae9e377033ea', N'visa', N'1668', 1, '2026-05-20T16:30:00.000'),
        ((SELECT customer_id FROM @SeedCustomers WHERE customer_reference = N'DEMO-PL-C0070'), N'PROC_A', N'acct_test_proc_a_m05', N'tok_test_pl_18690f4bb5dae68d14f94e8544bd0bb2', N'mastercard', N'5053', 1, '2026-10-02T03:23:00.000'),
        ((SELECT customer_id FROM @SeedCustomers WHERE customer_reference = N'DEMO-PL-C0070'), N'PROC_A', N'acct_test_proc_a_m05', N'tok_test_pl_1c75e7cfcfe7024d7ddcd23a4c981f4c', N'mastercard', N'3035', 1, '2026-10-02T15:23:00.000'),
        ((SELECT customer_id FROM @SeedCustomers WHERE customer_reference = N'DEMO-PL-C0071'), N'PROC_A', N'acct_test_proc_a_m04', N'tok_test_pl_e384e31f765d1b343df25051224ef9ef', N'visa', N'3235', 1, '2026-10-03T21:12:00.000'),
        ((SELECT customer_id FROM @SeedCustomers WHERE customer_reference = N'DEMO-PL-C0072'), N'PROC_A', N'acct_test_proc_a_m04', N'tok_test_pl_6bf67f9804d8d359b183b3964039ccc3', N'mastercard', N'3089', 1, '2026-05-28T21:22:00.000'),
        ((SELECT customer_id FROM @SeedCustomers WHERE customer_reference = N'DEMO-PL-C0073'), N'PROC_A', N'acct_test_proc_a_m01', N'tok_test_pl_9d2b961aa017ff5749a22dd1c35ea3c8', N'visa', N'8833', 1, '2026-08-31T19:50:00.000'),
        ((SELECT customer_id FROM @SeedCustomers WHERE customer_reference = N'DEMO-PL-C0073'), N'PROC_A', N'acct_test_proc_a_m01', N'tok_test_pl_d0cf43a79a9989f912570f679d61c751', N'visa', N'9559', 1, '2026-09-01T10:50:00.000'),
        ((SELECT customer_id FROM @SeedCustomers WHERE customer_reference = N'DEMO-PL-C0074'), N'PROC_A', N'acct_test_proc_a_m05', N'tok_test_pl_a69c7d4f0236d41b66fcffa1bdbb72c2', N'visa', N'2155', 1, '2026-06-06T21:11:00.000'),
        ((SELECT customer_id FROM @SeedCustomers WHERE customer_reference = N'DEMO-PL-C0075'), N'PROC_A', N'acct_test_proc_a_m01', N'tok_test_pl_9649378cdef918598c73a588feb1fb2a', N'mastercard', N'0790', 1, '2026-07-07T04:47:00.000'),
        ((SELECT customer_id FROM @SeedCustomers WHERE customer_reference = N'DEMO-PL-C0076'), N'PROC_A', N'acct_test_proc_a_m03', N'tok_test_pl_d6a21d82ddf8b2603cd1a52b5d385855', N'visa', N'8584', 1, '2026-09-04T11:39:00.000'),
        ((SELECT customer_id FROM @SeedCustomers WHERE customer_reference = N'DEMO-PL-C0077'), N'PROC_A', N'acct_test_proc_a_m04', N'tok_test_pl_a914be8b6ad1e792ddfd5ccb389530b6', N'mastercard', N'8530', 1, '2026-05-04T22:32:00.000'),
        ((SELECT customer_id FROM @SeedCustomers WHERE customer_reference = N'DEMO-PL-C0078'), N'PROC_A', N'acct_test_proc_a_m05', N'tok_test_pl_aff9cd4eb24f54b706c1d9f2f6b854c1', N'mastercard', N'1738', 1, '2026-06-25T00:28:00.000'),
        ((SELECT customer_id FROM @SeedCustomers WHERE customer_reference = N'DEMO-PL-C0079'), N'PROC_A', N'acct_test_proc_a_m01', N'tok_test_pl_35f8d6b688694d2c732e16d06716ec98', N'mastercard', N'2722', 1, '2026-08-13T05:51:00.000'),
        ((SELECT customer_id FROM @SeedCustomers WHERE customer_reference = N'DEMO-PL-C0080'), N'PROC_A', N'acct_test_proc_a_m05', N'tok_test_pl_d5122f3423be0d6b3aaaae5af184a802', N'mastercard', N'3480', 1, '2026-09-01T22:46:00.000'),
        ((SELECT customer_id FROM @SeedCustomers WHERE customer_reference = N'DEMO-PL-C0081'), N'PROC_A', N'acct_test_proc_a_m04', N'tok_test_pl_2bd110a3e8c1177ab8505640434c6464', N'visa', N'3263', 1, '2026-07-30T07:31:00.000'),
        ((SELECT customer_id FROM @SeedCustomers WHERE customer_reference = N'DEMO-PL-C0082'), N'PROC_A', N'acct_test_proc_a_m03', N'tok_test_pl_f683468576deab9e07ab5ac9a5d8f833', N'visa', N'8234', 1, '2026-08-02T01:49:00.000'),
        ((SELECT customer_id FROM @SeedCustomers WHERE customer_reference = N'DEMO-PL-C0083'), N'PROC_A', N'acct_test_proc_a_m02', N'tok_test_pl_ce6f0286534a2cf267748f65d9903f04', N'mastercard', N'5554', 1, '2026-06-22T09:08:00.000'),
        ((SELECT customer_id FROM @SeedCustomers WHERE customer_reference = N'DEMO-PL-C0083'), N'PROC_A', N'acct_test_proc_a_m02', N'tok_test_pl_3d9f225775905f4a47fc11f00da5f328', N'visa', N'9736', 1, '2026-06-20T22:08:00.000'),
        ((SELECT customer_id FROM @SeedCustomers WHERE customer_reference = N'DEMO-PL-C0084'), N'PROC_A', N'acct_test_proc_a_m02', N'tok_test_pl_7ba41379a04466c2b7c906e839758b3b', N'visa', N'9854', 1, '2026-06-25T00:44:00.000'),
        ((SELECT customer_id FROM @SeedCustomers WHERE customer_reference = N'DEMO-PL-C0085'), N'PROC_A', N'acct_test_proc_a_m03', N'tok_test_pl_bacece706874acc77ecd5b2f853fe3f1', N'visa', N'8985', 1, '2026-10-18T17:59:00.000'),
        ((SELECT customer_id FROM @SeedCustomers WHERE customer_reference = N'DEMO-PL-C0086'), N'PROC_A', N'acct_test_proc_a_m03', N'tok_test_pl_d77e8eb2691566152c61c3e3f6d8cc22', N'mastercard', N'2093', 1, '2026-05-21T17:17:00.000'),
        ((SELECT customer_id FROM @SeedCustomers WHERE customer_reference = N'DEMO-PL-C0087'), N'PROC_A', N'acct_test_proc_a_m03', N'tok_test_pl_e5cdc03b32a459c8bfabec6bba5d0f5d', N'mastercard', N'7633', 1, '2026-05-21T07:13:00.000'),
        ((SELECT customer_id FROM @SeedCustomers WHERE customer_reference = N'DEMO-PL-C0088'), N'PROC_A', N'acct_test_proc_a_m03', N'tok_test_pl_9d91eb991fc85ec450b297b62abffe11', N'visa', N'0915', 1, '2026-08-27T22:44:00.000'),
        ((SELECT customer_id FROM @SeedCustomers WHERE customer_reference = N'DEMO-PL-C0089'), N'PROC_A', N'acct_test_proc_a_m02', N'tok_test_pl_2f454685cdc38dff41f6631a519538ba', N'visa', N'3138', 1, '2026-08-11T13:32:00.000'),
        ((SELECT customer_id FROM @SeedCustomers WHERE customer_reference = N'DEMO-PL-C0089'), N'PROC_A', N'acct_test_proc_a_m02', N'tok_test_pl_0e8e7db3f0ad126b24395c7239927147', N'visa', N'1665', 0, '2026-08-10T17:32:00.000'),
        ((SELECT customer_id FROM @SeedCustomers WHERE customer_reference = N'DEMO-PL-C0090'), N'PROC_A', N'acct_test_proc_a_m02', N'tok_test_pl_507f3d388d7baa589acbf8dbe3babb84', N'mastercard', N'5052', 1, '2026-07-28T10:23:00.000'),
        ((SELECT customer_id FROM @SeedCustomers WHERE customer_reference = N'DEMO-PL-C0090'), N'PROC_A', N'acct_test_proc_a_m02', N'tok_test_pl_633aba513d5a3dec5819e810d08768f9', N'mastercard', N'5318', 1, '2026-07-27T07:23:00.000'),
        ((SELECT customer_id FROM @SeedCustomers WHERE customer_reference = N'DEMO-PL-C0091'), N'PROC_A', N'acct_test_proc_a_m03', N'tok_test_pl_589217017492f98a7a7164668e256552', N'mastercard', N'1786', 1, '2026-11-08T20:00:00.000'),
        ((SELECT customer_id FROM @SeedCustomers WHERE customer_reference = N'DEMO-PL-C0092'), N'PROC_A', N'acct_test_proc_a_m01', N'tok_test_pl_2a11984539e97da1269459cafeb671eb', N'mastercard', N'9217', 1, '2026-10-06T16:19:00.000'),
        ((SELECT customer_id FROM @SeedCustomers WHERE customer_reference = N'DEMO-PL-C0093'), N'PROC_A', N'acct_test_proc_a_m02', N'tok_test_pl_e7c5793c4dd08a33e3f1d2f2c43ba83e', N'mastercard', N'8042', 1, '2026-05-07T23:25:00.000'),
        ((SELECT customer_id FROM @SeedCustomers WHERE customer_reference = N'DEMO-PL-C0094'), N'PROC_A', N'acct_test_proc_a_m03', N'tok_test_pl_91028080678f3cfd652b9a21b7d0b7c7', N'visa', N'0824', 1, '2026-09-16T17:14:00.000'),
        ((SELECT customer_id FROM @SeedCustomers WHERE customer_reference = N'DEMO-PL-C0095'), N'PROC_A', N'acct_test_proc_a_m04', N'tok_test_pl_3d1ef16632ab1741e379e4de2fe7a520', N'visa', N'0737', 1, '2026-06-11T01:28:00.000'),
        ((SELECT customer_id FROM @SeedCustomers WHERE customer_reference = N'DEMO-PL-C0096'), N'PROC_A', N'acct_test_proc_a_m05', N'tok_test_pl_4be16c690bb0e6fd49c094aa69237ca4', N'visa', N'1408', 1, '2026-09-27T13:22:00.000'),
        ((SELECT customer_id FROM @SeedCustomers WHERE customer_reference = N'DEMO-PL-C0096'), N'PROC_A', N'acct_test_proc_a_m05', N'tok_test_pl_c2eb2678f7c2d5050fa950e3dfd9061f', N'visa', N'4824', 0, '2026-09-28T17:22:00.000'),
        ((SELECT customer_id FROM @SeedCustomers WHERE customer_reference = N'DEMO-PL-C0097'), N'PROC_A', N'acct_test_proc_a_m04', N'tok_test_pl_ae53fa41de4d30b3e3b3288a27e4c3c8', N'visa', N'9286', 1, '2026-06-01T08:31:00.000'),
        ((SELECT customer_id FROM @SeedCustomers WHERE customer_reference = N'DEMO-PL-C0098'), N'PROC_A', N'acct_test_proc_a_m03', N'tok_test_pl_d4a5ce49f9fc6bcebd4778021ce14550', N'visa', N'2902', 1, '2026-10-19T20:16:00.000'),
        ((SELECT customer_id FROM @SeedCustomers WHERE customer_reference = N'DEMO-PL-C0098'), N'PROC_A', N'acct_test_proc_a_m03', N'tok_test_pl_1b0d9414f27c3cdd3b2bdf25e85a3b13', N'mastercard', N'9825', 1, '2026-10-20T09:16:00.000'),
        ((SELECT customer_id FROM @SeedCustomers WHERE customer_reference = N'DEMO-PL-C0099'), N'PROC_A', N'acct_test_proc_a_m04', N'tok_test_pl_341772f9c564db6d56cb9086b6bddbf9', N'mastercard', N'0935', 1, '2026-07-31T14:49:00.000'),
        ((SELECT customer_id FROM @SeedCustomers WHERE customer_reference = N'DEMO-PL-C0100'), N'PROC_A', N'acct_test_proc_a_m05', N'tok_test_pl_eee9e32a4efe4d1b29f1437cb6151a82', N'visa', N'1594', 1, '2026-06-12T10:52:00.000'),
        ((SELECT customer_id FROM @SeedCustomers WHERE customer_reference = N'DEMO-PL-C0101'), N'PROC_A', N'acct_test_proc_a_m03', N'tok_test_pl_eeab90fa35763271955a0c3115b7453a', N'visa', N'6827', 1, '2026-06-19T03:12:00.000'),
        ((SELECT customer_id FROM @SeedCustomers WHERE customer_reference = N'DEMO-PL-C0102'), N'PROC_A', N'acct_test_proc_a_m04', N'tok_test_pl_81b70780e354db156880b9f8c34ffbe2', N'mastercard', N'9007', 1, '2026-10-18T11:11:00.000'),
        ((SELECT customer_id FROM @SeedCustomers WHERE customer_reference = N'DEMO-PL-C0103'), N'PROC_A', N'acct_test_proc_a_m03', N'tok_test_pl_f393b1d78152f8e5318be5bf3c71d101', N'mastercard', N'7826', 1, '2026-08-12T22:40:00.000'),
        ((SELECT customer_id FROM @SeedCustomers WHERE customer_reference = N'DEMO-PL-C0104'), N'PROC_A', N'acct_test_proc_a_m02', N'tok_test_pl_a524a358f373e840552bec2c4c5df319', N'visa', N'6873', 1, '2026-10-12T19:09:00.000'),
        ((SELECT customer_id FROM @SeedCustomers WHERE customer_reference = N'DEMO-PL-C0104'), N'PROC_A', N'acct_test_proc_a_m02', N'tok_test_pl_b2f41a70424dc46c7e2aa1c69ba38ca9', N'mastercard', N'0134', 1, '2026-10-12T23:09:00.000'),
        ((SELECT customer_id FROM @SeedCustomers WHERE customer_reference = N'DEMO-PL-C0105'), N'PROC_A', N'acct_test_proc_a_m01', N'tok_test_pl_aaae45a49fb2031fe20b30a29d26aa72', N'visa', N'8507', 1, '2026-07-20T09:16:00.000'),
        ((SELECT customer_id FROM @SeedCustomers WHERE customer_reference = N'DEMO-PL-C0106'), N'PROC_A', N'acct_test_proc_a_m04', N'tok_test_pl_6ad67bff2e8f3c41ea948d9436c51112', N'visa', N'8080', 1, '2026-04-27T06:26:00.000'),
        ((SELECT customer_id FROM @SeedCustomers WHERE customer_reference = N'DEMO-PL-C0107'), N'PROC_A', N'acct_test_proc_a_m03', N'tok_test_pl_149eee14eec4d4ef57537863bbe23366', N'mastercard', N'7249', 1, '2026-09-27T00:23:00.000'),
        ((SELECT customer_id FROM @SeedCustomers WHERE customer_reference = N'DEMO-PL-C0108'), N'PROC_A', N'acct_test_proc_a_m04', N'tok_test_pl_dd7e25ccf9d04e2bcf744ec5d41a5bbc', N'mastercard', N'8168', 1, '2026-05-15T08:22:00.000'),
        ((SELECT customer_id FROM @SeedCustomers WHERE customer_reference = N'DEMO-PL-C0109'), N'PROC_A', N'acct_test_proc_a_m05', N'tok_test_pl_0aa9f05ce89fbb60fe2ef27a6a9a822c', N'visa', N'1958', 1, '2026-05-03T06:06:00.000'),
        ((SELECT customer_id FROM @SeedCustomers WHERE customer_reference = N'DEMO-PL-C0110'), N'PROC_A', N'acct_test_proc_a_m02', N'tok_test_pl_65075de2672fa275780d0f3d5e08e014', N'mastercard', N'0281', 1, '2026-05-19T22:52:00.000'),
        ((SELECT customer_id FROM @SeedCustomers WHERE customer_reference = N'DEMO-PL-C0111'), N'PROC_A', N'acct_test_proc_a_m03', N'tok_test_pl_f145101755e593f158150a55b8c0e53c', N'mastercard', N'5710', 1, '2026-07-22T08:45:00.000'),
        ((SELECT customer_id FROM @SeedCustomers WHERE customer_reference = N'DEMO-PL-C0112'), N'PROC_A', N'acct_test_proc_a_m02', N'tok_test_pl_760fa5cbae874fc1699b1e0eab073628', N'visa', N'6868', 1, '2026-07-08T10:04:00.000'),
        ((SELECT customer_id FROM @SeedCustomers WHERE customer_reference = N'DEMO-PL-C0112'), N'PROC_A', N'acct_test_proc_a_m02', N'tok_test_pl_a77ef509dc21fa517c01c5b50673ea3c', N'mastercard', N'2693', 1, '2026-07-07T14:04:00.000'),
        ((SELECT customer_id FROM @SeedCustomers WHERE customer_reference = N'DEMO-PL-C0113'), N'PROC_A', N'acct_test_proc_a_m03', N'tok_test_pl_0b3aa1e523e024cd25bed7e792105704', N'visa', N'8471', 1, '2026-09-04T12:38:00.000'),
        ((SELECT customer_id FROM @SeedCustomers WHERE customer_reference = N'DEMO-PL-C0114'), N'PROC_A', N'acct_test_proc_a_m03', N'tok_test_pl_76ec8a31d69365afb13a6e4748f47ee9', N'mastercard', N'9345', 1, '2026-06-10T10:22:00.000'),
        ((SELECT customer_id FROM @SeedCustomers WHERE customer_reference = N'DEMO-PL-C0114'), N'PROC_A', N'acct_test_proc_a_m03', N'tok_test_pl_dd13b9f39849f4319890611caa5342f8', N'mastercard', N'6389', 1, '2026-06-09T14:22:00.000'),
        ((SELECT customer_id FROM @SeedCustomers WHERE customer_reference = N'DEMO-PL-C0115'), N'PROC_A', N'acct_test_proc_a_m05', N'tok_test_pl_6722328c74767f73527a4f4e87e9f262', N'mastercard', N'4940', 1, '2026-04-20T11:44:00.000'),
        ((SELECT customer_id FROM @SeedCustomers WHERE customer_reference = N'DEMO-PL-C0115'), N'PROC_A', N'acct_test_proc_a_m05', N'tok_test_pl_5f546bf7498cba96cf3dca2ef5b846c3', N'visa', N'1129', 1, '2026-04-20T01:44:00.000'),
        ((SELECT customer_id FROM @SeedCustomers WHERE customer_reference = N'DEMO-PL-C0116'), N'PROC_A', N'acct_test_proc_a_m02', N'tok_test_pl_1ba9721aff538c61f258170ea20776f2', N'mastercard', N'2159', 1, '2026-07-09T06:24:00.000'),
        ((SELECT customer_id FROM @SeedCustomers WHERE customer_reference = N'DEMO-PL-C0117'), N'PROC_A', N'acct_test_proc_a_m05', N'tok_test_pl_ff93d34f1c0544fb3bd7bf68391171cf', N'mastercard', N'7503', 1, '2026-10-17T11:54:00.000'),
        ((SELECT customer_id FROM @SeedCustomers WHERE customer_reference = N'DEMO-PL-C0117'), N'PROC_A', N'acct_test_proc_a_m05', N'tok_test_pl_e70c9b02a79c89fdf5896957ffb02d79', N'mastercard', N'5336', 1, '2026-10-17T03:54:00.000'),
        ((SELECT customer_id FROM @SeedCustomers WHERE customer_reference = N'DEMO-PL-C0118'), N'PROC_A', N'acct_test_proc_a_m05', N'tok_test_pl_1d5add7e982a9e54fa0d17049e98152a', N'visa', N'1875', 1, '2026-08-22T11:46:00.000'),
        ((SELECT customer_id FROM @SeedCustomers WHERE customer_reference = N'DEMO-PL-C0119'), N'PROC_A', N'acct_test_proc_a_m01', N'tok_test_pl_60f087dd80238fc339327abb4fa9d439', N'mastercard', N'4770', 1, '2026-05-27T23:56:00.000'),
        ((SELECT customer_id FROM @SeedCustomers WHERE customer_reference = N'DEMO-PL-C0120'), N'PROC_A', N'acct_test_proc_a_m01', N'tok_test_pl_ca5cb93e002e65aea9d9bf31975109f0', N'mastercard', N'4155', 1, '2026-05-24T10:23:00.000'),
        ((SELECT customer_id FROM @SeedCustomers WHERE customer_reference = N'DEMO-PL-C0121'), N'PROC_A', N'acct_test_proc_a_m02', N'tok_test_pl_581ea378d6302e1b56eb170f247b2878', N'visa', N'8494', 1, '2026-05-23T22:33:00.000'),
        ((SELECT customer_id FROM @SeedCustomers WHERE customer_reference = N'DEMO-PL-C0121'), N'PROC_A', N'acct_test_proc_a_m02', N'tok_test_pl_6bf00b8c03058b2da4bd182a219974ff', N'mastercard', N'1095', 0, '2026-05-22T20:33:00.000'),
        ((SELECT customer_id FROM @SeedCustomers WHERE customer_reference = N'DEMO-PL-C0122'), N'PROC_A', N'acct_test_proc_a_m01', N'tok_test_pl_d5691e14886c1eeb86c8291a347fda3c', N'visa', N'2873', 1, '2026-07-19T06:03:00.000'),
        ((SELECT customer_id FROM @SeedCustomers WHERE customer_reference = N'DEMO-PL-C0123'), N'PROC_A', N'acct_test_proc_a_m01', N'tok_test_pl_de70e0a2c4ab3d1204cdd48f17b95d7f', N'mastercard', N'1493', 1, '2026-07-17T12:02:00.000'),
        ((SELECT customer_id FROM @SeedCustomers WHERE customer_reference = N'DEMO-PL-C0123'), N'PROC_A', N'acct_test_proc_a_m01', N'tok_test_pl_33e0eec0d33a0e898e93b3f07933dc16', N'mastercard', N'1580', 1, '2026-07-15T10:02:00.000'),
        ((SELECT customer_id FROM @SeedCustomers WHERE customer_reference = N'DEMO-PL-C0124'), N'PROC_A', N'acct_test_proc_a_m04', N'tok_test_pl_b4668fe03be4c7dac1bebb6b1e7295c5', N'mastercard', N'8868', 1, '2026-08-21T14:35:00.000'),
        ((SELECT customer_id FROM @SeedCustomers WHERE customer_reference = N'DEMO-PL-C0124'), N'PROC_A', N'acct_test_proc_a_m04', N'tok_test_pl_32fb640e2e0e93d4ac7d5c8108e342d7', N'visa', N'2108', 1, '2026-08-21T02:35:00.000'),
        ((SELECT customer_id FROM @SeedCustomers WHERE customer_reference = N'DEMO-PL-C0125'), N'PROC_A', N'acct_test_proc_a_m04', N'tok_test_pl_4f5344d61dde95b97ad5e0484af5ab82', N'visa', N'3913', 1, '2026-10-17T03:53:00.000'),
        ((SELECT customer_id FROM @SeedCustomers WHERE customer_reference = N'DEMO-PL-C0126'), N'PROC_A', N'acct_test_proc_a_m02', N'tok_test_pl_92408b792162d5c08bec41b2bae7b66c', N'mastercard', N'9524', 1, '2026-07-13T14:24:00.000'),
        ((SELECT customer_id FROM @SeedCustomers WHERE customer_reference = N'DEMO-PL-C0126'), N'PROC_A', N'acct_test_proc_a_m02', N'tok_test_pl_25b245e846cbf7e06019a190ffb37902', N'visa', N'5629', 1, '2026-07-13T02:24:00.000'),
        ((SELECT customer_id FROM @SeedCustomers WHERE customer_reference = N'DEMO-PL-C0127'), N'PROC_A', N'acct_test_proc_a_m04', N'tok_test_pl_eb3615b0c3848078c94c0985a2b7d1c6', N'visa', N'6798', 1, '2026-08-15T22:21:00.000'),
        ((SELECT customer_id FROM @SeedCustomers WHERE customer_reference = N'DEMO-PL-C0127'), N'PROC_A', N'acct_test_proc_a_m04', N'tok_test_pl_82a4b953ca28e6132056b10aab259b8d', N'mastercard', N'9627', 1, '2026-08-17T20:21:00.000'),
        ((SELECT customer_id FROM @SeedCustomers WHERE customer_reference = N'DEMO-PL-C0128'), N'PROC_A', N'acct_test_proc_a_m01', N'tok_test_pl_c3fd9c1210da7a0a47c1c7d46f357da6', N'visa', N'1197', 1, '2026-09-11T17:48:00.000'),
        ((SELECT customer_id FROM @SeedCustomers WHERE customer_reference = N'DEMO-PL-C0128'), N'PROC_A', N'acct_test_proc_a_m01', N'tok_test_pl_27e67fe3a000f6699781cb602922e862', N'mastercard', N'5461', 0, '2026-09-12T16:48:00.000'),
        ((SELECT customer_id FROM @SeedCustomers WHERE customer_reference = N'DEMO-PL-C0129'), N'PROC_A', N'acct_test_proc_a_m05', N'tok_test_pl_ec69def078295b9261e0eb3814fd8028', N'visa', N'6506', 1, '2026-07-31T05:15:00.000'),
        ((SELECT customer_id FROM @SeedCustomers WHERE customer_reference = N'DEMO-PL-C0130'), N'PROC_A', N'acct_test_proc_a_m05', N'tok_test_pl_c11f9eefad2a6ec3ea642dec6c2cb73b', N'visa', N'6061', 1, '2026-04-14T20:19:00.000'),
        ((SELECT customer_id FROM @SeedCustomers WHERE customer_reference = N'DEMO-PL-C0130'), N'PROC_A', N'acct_test_proc_a_m05', N'tok_test_pl_5a950c8baba8b31fa9fd59a152b1ab69', N'visa', N'8484', 0, '2026-04-14T04:19:00.000'),
        ((SELECT customer_id FROM @SeedCustomers WHERE customer_reference = N'DEMO-PL-C0131'), N'PROC_A', N'acct_test_proc_a_m02', N'tok_test_pl_61337f0a22da8c487601c7b06266b100', N'mastercard', N'4717', 1, '2026-07-19T19:04:00.000'),
        ((SELECT customer_id FROM @SeedCustomers WHERE customer_reference = N'DEMO-PL-C0131'), N'PROC_A', N'acct_test_proc_a_m02', N'tok_test_pl_4528266413a96ee785e936178f1b7676', N'mastercard', N'5392', 1, '2026-07-20T05:04:00.000'),
        ((SELECT customer_id FROM @SeedCustomers WHERE customer_reference = N'DEMO-PL-C0132'), N'PROC_A', N'acct_test_proc_a_m03', N'tok_test_pl_dc2d4bedf5fde51bac1e5bd37e21389a', N'mastercard', N'5924', 1, '2026-06-09T07:08:00.000'),
        ((SELECT customer_id FROM @SeedCustomers WHERE customer_reference = N'DEMO-PL-C0132'), N'PROC_A', N'acct_test_proc_a_m03', N'tok_test_pl_fc35fd310d67df6bd8bf971ada9bb28a', N'mastercard', N'2749', 0, '2026-06-10T06:08:00.000'),
        ((SELECT customer_id FROM @SeedCustomers WHERE customer_reference = N'DEMO-PL-C0133'), N'PROC_A', N'acct_test_proc_a_m04', N'tok_test_pl_c30f7539f9c0b4702602fba005fb561b', N'visa', N'5719', 1, '2026-08-01T22:05:00.000'),
        ((SELECT customer_id FROM @SeedCustomers WHERE customer_reference = N'DEMO-PL-C0133'), N'PROC_A', N'acct_test_proc_a_m04', N'tok_test_pl_63335ef115e58cc6948aae105c5804e0', N'mastercard', N'6284', 1, '2026-08-04T04:05:00.000'),
        ((SELECT customer_id FROM @SeedCustomers WHERE customer_reference = N'DEMO-PL-C0134'), N'PROC_A', N'acct_test_proc_a_m02', N'tok_test_pl_e94d67084c2c2bed4e211ec1810b2fd8', N'mastercard', N'4226', 1, '2026-07-18T00:57:00.000'),
        ((SELECT customer_id FROM @SeedCustomers WHERE customer_reference = N'DEMO-PL-C0135'), N'PROC_A', N'acct_test_proc_a_m04', N'tok_test_pl_ce347a4ea9a4734300b212eee2e68a41', N'visa', N'8667', 1, '2026-09-08T16:55:00.000'),
        ((SELECT customer_id FROM @SeedCustomers WHERE customer_reference = N'DEMO-PL-C0135'), N'PROC_A', N'acct_test_proc_a_m04', N'tok_test_pl_22e7285e04f9703271c89637b0e02b7a', N'mastercard', N'0977', 1, '2026-09-08T09:55:00.000'),
        ((SELECT customer_id FROM @SeedCustomers WHERE customer_reference = N'DEMO-PL-C0136'), N'PROC_A', N'acct_test_proc_a_m03', N'tok_test_pl_717b3af0861fc2363c9251e312a93875', N'visa', N'9862', 1, '2026-05-02T23:12:00.000'),
        ((SELECT customer_id FROM @SeedCustomers WHERE customer_reference = N'DEMO-PL-C0137'), N'PROC_A', N'acct_test_proc_a_m05', N'tok_test_pl_fb219f3c639e156bbaed7560cad2dc45', N'mastercard', N'0335', 1, '2026-09-20T03:31:00.000'),
        ((SELECT customer_id FROM @SeedCustomers WHERE customer_reference = N'DEMO-PL-C0137'), N'PROC_A', N'acct_test_proc_a_m05', N'tok_test_pl_6dfa9790edcfe24a611fc70bf721f8af', N'mastercard', N'0774', 1, '2026-09-20T12:31:00.000'),
        ((SELECT customer_id FROM @SeedCustomers WHERE customer_reference = N'DEMO-PL-C0138'), N'PROC_A', N'acct_test_proc_a_m03', N'tok_test_pl_3b7803d38bc7cf4da71e9ef7f426e631', N'visa', N'8578', 1, '2026-08-23T23:18:00.000'),
        ((SELECT customer_id FROM @SeedCustomers WHERE customer_reference = N'DEMO-PL-C0139'), N'PROC_A', N'acct_test_proc_a_m05', N'tok_test_pl_1378dae0e3e9ed4288edf7ddea33dc49', N'mastercard', N'9517', 1, '2026-09-15T09:24:00.000'),
        ((SELECT customer_id FROM @SeedCustomers WHERE customer_reference = N'DEMO-PL-C0140'), N'PROC_A', N'acct_test_proc_a_m04', N'tok_test_pl_55214d407a0c23a076e86f7f26653f6a', N'visa', N'7532', 1, '2026-05-05T21:33:00.000'),
        ((SELECT customer_id FROM @SeedCustomers WHERE customer_reference = N'DEMO-PL-C0140'), N'PROC_A', N'acct_test_proc_a_m04', N'tok_test_pl_114dd16acccca039830ba3f7a8acbcd3', N'visa', N'3856', 1, '2026-05-05T08:33:00.000'),
        ((SELECT customer_id FROM @SeedCustomers WHERE customer_reference = N'DEMO-PL-C0141'), N'PROC_A', N'acct_test_proc_a_m03', N'tok_test_pl_50167e7bcf0424d11ff9ed2f8edbb60a', N'visa', N'2582', 1, '2026-08-31T07:17:00.000'),
        ((SELECT customer_id FROM @SeedCustomers WHERE customer_reference = N'DEMO-PL-C0142'), N'PROC_A', N'acct_test_proc_a_m01', N'tok_test_pl_202f5f676454a2c3123c59f0eaad386c', N'mastercard', N'5622', 1, '2026-05-09T04:03:00.000'),
        ((SELECT customer_id FROM @SeedCustomers WHERE customer_reference = N'DEMO-PL-C0143'), N'PROC_A', N'acct_test_proc_a_m05', N'tok_test_pl_3a90fe1386bb5967743d3758a9f608d1', N'visa', N'0862', 1, '2026-09-02T15:19:00.000'),
        ((SELECT customer_id FROM @SeedCustomers WHERE customer_reference = N'DEMO-PL-C0144'), N'PROC_A', N'acct_test_proc_a_m02', N'tok_test_pl_cab599be97cff118891f90ef5b88a8ee', N'visa', N'8421', 1, '2026-07-13T13:20:00.000'),
        ((SELECT customer_id FROM @SeedCustomers WHERE customer_reference = N'DEMO-PL-C0145'), N'PROC_A', N'acct_test_proc_a_m04', N'tok_test_pl_099243f5eea031fd305d5de2c370f671', N'mastercard', N'8218', 1, '2026-11-07T13:59:00.000'),
        ((SELECT customer_id FROM @SeedCustomers WHERE customer_reference = N'DEMO-PL-C0145'), N'PROC_A', N'acct_test_proc_a_m04', N'tok_test_pl_992ac550b7089f1c11c88fc97af6d0c5', N'visa', N'7949', 1, '2026-11-06T22:59:00.000'),
        ((SELECT customer_id FROM @SeedCustomers WHERE customer_reference = N'DEMO-PL-C0146'), N'PROC_A', N'acct_test_proc_a_m04', N'tok_test_pl_b3c0a8beb81d3eff68e74f6cce181b2d', N'mastercard', N'3952', 1, '2026-10-26T06:37:00.000'),
        ((SELECT customer_id FROM @SeedCustomers WHERE customer_reference = N'DEMO-PL-C0146'), N'PROC_A', N'acct_test_proc_a_m04', N'tok_test_pl_37a7967d3f5c7fbb7ab8eb83cc99478d', N'mastercard', N'0942', 1, '2026-10-26T18:37:00.000'),
        ((SELECT customer_id FROM @SeedCustomers WHERE customer_reference = N'DEMO-PL-C0147'), N'PROC_A', N'acct_test_proc_a_m02', N'tok_test_pl_a73b1f5bd2a508be27f3e2ed820c9996', N'mastercard', N'7921', 1, '2026-09-09T14:40:00.000'),
        ((SELECT customer_id FROM @SeedCustomers WHERE customer_reference = N'DEMO-PL-C0148'), N'PROC_A', N'acct_test_proc_a_m05', N'tok_test_pl_cb22235f2278f8e6e6691106725d736b', N'mastercard', N'2860', 1, '2026-08-21T13:17:00.000'),
        ((SELECT customer_id FROM @SeedCustomers WHERE customer_reference = N'DEMO-PL-C0149'), N'PROC_A', N'acct_test_proc_a_m04', N'tok_test_pl_dc9c837dd19cdc55a2a960b99a1c0f35', N'mastercard', N'8067', 1, '2026-05-01T12:32:00.000'),
        ((SELECT customer_id FROM @SeedCustomers WHERE customer_reference = N'DEMO-PL-C0149'), N'PROC_A', N'acct_test_proc_a_m04', N'tok_test_pl_b7b11f8fb6f5cf168f70d8185207c6f6', N'visa', N'3420', 1, '2026-04-30T17:32:00.000'),
        ((SELECT customer_id FROM @SeedCustomers WHERE customer_reference = N'DEMO-PL-C0150'), N'PROC_A', N'acct_test_proc_a_m02', N'tok_test_pl_1624b617f86df6e73d659852b2769f6e', N'visa', N'2191', 1, '2026-10-17T03:03:00.000'),
        ((SELECT customer_id FROM @SeedCustomers WHERE customer_reference = N'DEMO-PL-C0150'), N'PROC_A', N'acct_test_proc_a_m02', N'tok_test_pl_9ab4fe9a280ad1a9eec610e564be062c', N'visa', N'7903', 1, '2026-10-17T04:03:00.000'),
        ((SELECT customer_id FROM @SeedCustomers WHERE customer_reference = N'DEMO-PL-C0151'), N'PROC_A', N'acct_test_proc_a_m04', N'tok_test_pl_2868c576c43dba464fb28eac97ca2159', N'mastercard', N'6463', 1, '2026-10-30T10:31:00.000'),
        ((SELECT customer_id FROM @SeedCustomers WHERE customer_reference = N'DEMO-PL-C0151'), N'PROC_A', N'acct_test_proc_a_m04', N'tok_test_pl_25d2dce3f98e6a74d0aa6e196e5ab0d9', N'visa', N'1415', 1, '2026-10-29T13:31:00.000'),
        ((SELECT customer_id FROM @SeedCustomers WHERE customer_reference = N'DEMO-PL-C0152'), N'PROC_A', N'acct_test_proc_a_m03', N'tok_test_pl_e2f3c1b8487797e91fa4c80723ab8e82', N'mastercard', N'0728', 1, '2026-08-30T21:19:00.000'),
        ((SELECT customer_id FROM @SeedCustomers WHERE customer_reference = N'DEMO-PL-C0152'), N'PROC_A', N'acct_test_proc_a_m03', N'tok_test_pl_1330de8bb5d15d1736e0c415724e4a89', N'mastercard', N'1237', 1, '2026-08-31T13:19:00.000'),
        ((SELECT customer_id FROM @SeedCustomers WHERE customer_reference = N'DEMO-PL-C0153'), N'PROC_A', N'acct_test_proc_a_m02', N'tok_test_pl_67bbfb8b368dda259ad8eb3a89940e78', N'mastercard', N'8206', 1, '2026-05-02T14:32:00.000'),
        ((SELECT customer_id FROM @SeedCustomers WHERE customer_reference = N'DEMO-PL-C0154'), N'PROC_A', N'acct_test_proc_a_m04', N'tok_test_pl_0b5243f5bdfb4326f8b4c240934b9da4', N'visa', N'8552', 1, '2026-10-20T00:25:00.000'),
        ((SELECT customer_id FROM @SeedCustomers WHERE customer_reference = N'DEMO-PL-C0155'), N'PROC_A', N'acct_test_proc_a_m04', N'tok_test_pl_d4e142a916a88c85c2cacf87f43fd32a', N'mastercard', N'7660', 1, '2026-04-16T19:19:00.000'),
        ((SELECT customer_id FROM @SeedCustomers WHERE customer_reference = N'DEMO-PL-C0156'), N'PROC_A', N'acct_test_proc_a_m02', N'tok_test_pl_f1a45d3faa46e882e7ac461e7a4e33d5', N'visa', N'6836', 1, '2026-07-24T19:51:00.000'),
        ((SELECT customer_id FROM @SeedCustomers WHERE customer_reference = N'DEMO-PL-C0157'), N'PROC_A', N'acct_test_proc_a_m02', N'tok_test_pl_409bc1f1a7e59a5e7b31295d9f0150b7', N'visa', N'5100', 1, '2026-07-27T22:40:00.000'),
        ((SELECT customer_id FROM @SeedCustomers WHERE customer_reference = N'DEMO-PL-C0158'), N'PROC_A', N'acct_test_proc_a_m01', N'tok_test_pl_d8952870f8206384cc2088d19a5616ab', N'visa', N'3669', 1, '2026-07-11T08:03:00.000'),
        ((SELECT customer_id FROM @SeedCustomers WHERE customer_reference = N'DEMO-PL-C0158'), N'PROC_A', N'acct_test_proc_a_m01', N'tok_test_pl_a855c52e5ec8d1dec53bb32dd5feaa43', N'visa', N'1088', 1, '2026-07-11T22:03:00.000'),
        ((SELECT customer_id FROM @SeedCustomers WHERE customer_reference = N'DEMO-PL-C0159'), N'PROC_A', N'acct_test_proc_a_m02', N'tok_test_pl_6574407aa6a08ed5ff6c343d587764aa', N'mastercard', N'0080', 1, '2026-08-13T14:03:00.000'),
        ((SELECT customer_id FROM @SeedCustomers WHERE customer_reference = N'DEMO-PL-C0160'), N'PROC_A', N'acct_test_proc_a_m02', N'tok_test_pl_9558ef52883e53ac8fa7e09ed4f15dc5', N'visa', N'9056', 1, '2026-06-27T23:08:00.000'),
        ((SELECT customer_id FROM @SeedCustomers WHERE customer_reference = N'DEMO-PL-C0161'), N'PROC_A', N'acct_test_proc_a_m01', N'tok_test_pl_a9394f4fa9da0a7330c5b427915ad578', N'visa', N'5618', 1, '2026-05-12T12:27:00.000'),
        ((SELECT customer_id FROM @SeedCustomers WHERE customer_reference = N'DEMO-PL-C0161'), N'PROC_A', N'acct_test_proc_a_m01', N'tok_test_pl_59d2dd2fff8dd4b15d4a30f4bdce6c9c', N'mastercard', N'7145', 0, '2026-05-12T01:27:00.000'),
        ((SELECT customer_id FROM @SeedCustomers WHERE customer_reference = N'DEMO-PL-C0162'), N'PROC_A', N'acct_test_proc_a_m03', N'tok_test_pl_73f57e3bebb0abf5c0e5e5da0dad5f3e', N'mastercard', N'4466', 1, '2026-05-01T13:47:00.000'),
        ((SELECT customer_id FROM @SeedCustomers WHERE customer_reference = N'DEMO-PL-C0163'), N'PROC_A', N'acct_test_proc_a_m01', N'tok_test_pl_690c2b52ea80982efeed0273b0df3da8', N'visa', N'1227', 1, '2026-04-29T00:36:00.000'),
        ((SELECT customer_id FROM @SeedCustomers WHERE customer_reference = N'DEMO-PL-C0164'), N'PROC_A', N'acct_test_proc_a_m03', N'tok_test_pl_b409eec36b8bd742afe4d8db96a3eb2c', N'visa', N'0931', 1, '2026-07-13T18:08:00.000'),
        ((SELECT customer_id FROM @SeedCustomers WHERE customer_reference = N'DEMO-PL-C0165'), N'PROC_A', N'acct_test_proc_a_m02', N'tok_test_pl_b483f3d980ce26100694a7dc162cfa6d', N'visa', N'7339', 1, '2026-08-16T09:25:00.000'),
        ((SELECT customer_id FROM @SeedCustomers WHERE customer_reference = N'DEMO-PL-C0165'), N'PROC_A', N'acct_test_proc_a_m02', N'tok_test_pl_89479f5f7c0c5d147ebc88e22b6d88e7', N'mastercard', N'3439', 1, '2026-08-18T10:25:00.000'),
        ((SELECT customer_id FROM @SeedCustomers WHERE customer_reference = N'DEMO-PL-C0166'), N'PROC_A', N'acct_test_proc_a_m01', N'tok_test_pl_8597eb927159860ba5715b8d08fc228b', N'visa', N'3210', 1, '2026-08-23T10:09:00.000'),
        ((SELECT customer_id FROM @SeedCustomers WHERE customer_reference = N'DEMO-PL-C0166'), N'PROC_A', N'acct_test_proc_a_m01', N'tok_test_pl_a9d089d253c23b15d9b72c2f6b5ddeb3', N'visa', N'8235', 1, '2026-08-23T00:09:00.000'),
        ((SELECT customer_id FROM @SeedCustomers WHERE customer_reference = N'DEMO-PL-C0167'), N'PROC_A', N'acct_test_proc_a_m02', N'tok_test_pl_9776cd821a8d5cf876c697fa0fd893d6', N'visa', N'7076', 1, '2026-06-14T21:02:00.000'),
        ((SELECT customer_id FROM @SeedCustomers WHERE customer_reference = N'DEMO-PL-C0168'), N'PROC_A', N'acct_test_proc_a_m02', N'tok_test_pl_7cf257254454b9f6bfb89fc42e94484a', N'visa', N'8554', 1, '2026-04-16T11:20:00.000'),
        ((SELECT customer_id FROM @SeedCustomers WHERE customer_reference = N'DEMO-PL-C0168'), N'PROC_A', N'acct_test_proc_a_m02', N'tok_test_pl_d7db037cdda10ac4fbbcd033bee4f167', N'mastercard', N'1414', 1, '2026-04-17T17:20:00.000'),
        ((SELECT customer_id FROM @SeedCustomers WHERE customer_reference = N'DEMO-PL-C0169'), N'PROC_A', N'acct_test_proc_a_m02', N'tok_test_pl_ebf3ec0b6800764fc8c06a7d5e9d7ed0', N'mastercard', N'7623', 1, '2026-07-04T00:39:00.000'),
        ((SELECT customer_id FROM @SeedCustomers WHERE customer_reference = N'DEMO-PL-C0170'), N'PROC_A', N'acct_test_proc_a_m03', N'tok_test_pl_ad5c0f1d8ac6f5c075bb91e68dab7347', N'visa', N'6971', 1, '2026-07-24T09:03:00.000'),
        ((SELECT customer_id FROM @SeedCustomers WHERE customer_reference = N'DEMO-PL-C0171'), N'PROC_A', N'acct_test_proc_a_m04', N'tok_test_pl_6db63a45bfe77058ed52041766995a2e', N'mastercard', N'0118', 1, '2026-06-21T16:59:00.000'),
        ((SELECT customer_id FROM @SeedCustomers WHERE customer_reference = N'DEMO-PL-C0171'), N'PROC_A', N'acct_test_proc_a_m04', N'tok_test_pl_cf2a29d4b39039167d9f5a16a25c4db8', N'visa', N'5715', 1, '2026-06-21T07:59:00.000'),
        ((SELECT customer_id FROM @SeedCustomers WHERE customer_reference = N'DEMO-PL-C0172'), N'PROC_A', N'acct_test_proc_a_m02', N'tok_test_pl_4049cb6f1c1c8dfcae6f72ecf9b6adec', N'mastercard', N'0125', 1, '2026-06-01T10:06:00.000'),
        ((SELECT customer_id FROM @SeedCustomers WHERE customer_reference = N'DEMO-PL-C0172'), N'PROC_A', N'acct_test_proc_a_m02', N'tok_test_pl_be4bc2eac01d351ebe8707f5cfaad4be', N'mastercard', N'3934', 1, '2026-05-31T23:06:00.000'),
        ((SELECT customer_id FROM @SeedCustomers WHERE customer_reference = N'DEMO-PL-C0173'), N'PROC_A', N'acct_test_proc_a_m05', N'tok_test_pl_284cb38daa7a0941364bb457f6e2006b', N'visa', N'9678', 1, '2026-09-18T19:57:00.000'),
        ((SELECT customer_id FROM @SeedCustomers WHERE customer_reference = N'DEMO-PL-C0174'), N'PROC_A', N'acct_test_proc_a_m01', N'tok_test_pl_e6728eb42a5e5b45b5c3b96cbf1ecc5b', N'mastercard', N'0944', 1, '2026-08-29T01:40:00.000'),
        ((SELECT customer_id FROM @SeedCustomers WHERE customer_reference = N'DEMO-PL-C0175'), N'PROC_A', N'acct_test_proc_a_m03', N'tok_test_pl_66c8183441e6dc4a5ad1e74590da895d', N'visa', N'9705', 1, '2026-04-24T00:00:00.000'),
        ((SELECT customer_id FROM @SeedCustomers WHERE customer_reference = N'DEMO-PL-C0175'), N'PROC_A', N'acct_test_proc_a_m03', N'tok_test_pl_b1aee71f1ab08972a1af3e5679a0cd37', N'mastercard', N'8266', 1, '2026-04-22T12:00:00.000'),
        ((SELECT customer_id FROM @SeedCustomers WHERE customer_reference = N'DEMO-PL-C0176'), N'PROC_A', N'acct_test_proc_a_m01', N'tok_test_pl_4be2a592693c9bca72acc7505e9bbd54', N'mastercard', N'8768', 1, '2026-05-04T05:44:00.000'),
        ((SELECT customer_id FROM @SeedCustomers WHERE customer_reference = N'DEMO-PL-C0176'), N'PROC_A', N'acct_test_proc_a_m01', N'tok_test_pl_5aacc35c4f0a16e9729799d0b29e7b87', N'visa', N'6624', 1, '2026-05-04T00:44:00.000'),
        ((SELECT customer_id FROM @SeedCustomers WHERE customer_reference = N'DEMO-PL-C0177'), N'PROC_A', N'acct_test_proc_a_m03', N'tok_test_pl_49010064d8669fa9994b18c2585175e0', N'mastercard', N'2159', 1, '2026-10-12T16:32:00.000'),
        ((SELECT customer_id FROM @SeedCustomers WHERE customer_reference = N'DEMO-PL-C0177'), N'PROC_A', N'acct_test_proc_a_m03', N'tok_test_pl_dc46e48fc6704c600fb3d14558a7507b', N'mastercard', N'4403', 1, '2026-10-12T08:32:00.000'),
        ((SELECT customer_id FROM @SeedCustomers WHERE customer_reference = N'DEMO-PL-C0178'), N'PROC_A', N'acct_test_proc_a_m01', N'tok_test_pl_2cbeaf8ee09400cfc9c6d92a7a8e0631', N'mastercard', N'4388', 1, '2026-08-25T20:58:00.000'),
        ((SELECT customer_id FROM @SeedCustomers WHERE customer_reference = N'DEMO-PL-C0179'), N'PROC_A', N'acct_test_proc_a_m05', N'tok_test_pl_62b6cd09d45c1acb8a82d00b6dda5426', N'visa', N'7219', 1, '2026-07-13T00:28:00.000'),
        ((SELECT customer_id FROM @SeedCustomers WHERE customer_reference = N'DEMO-PL-C0179'), N'PROC_A', N'acct_test_proc_a_m05', N'tok_test_pl_333154802808a3bc44ec342e13220bce', N'visa', N'2861', 1, '2026-07-11T19:28:00.000'),
        ((SELECT customer_id FROM @SeedCustomers WHERE customer_reference = N'DEMO-PL-C0180'), N'PROC_A', N'acct_test_proc_a_m04', N'tok_test_pl_282777cc2473bfd2aa8da4b7a8d0972d', N'visa', N'5600', 1, '2026-08-22T13:02:00.000'),
        ((SELECT customer_id FROM @SeedCustomers WHERE customer_reference = N'DEMO-PL-C0180'), N'PROC_A', N'acct_test_proc_a_m04', N'tok_test_pl_60e85d53df756de45675205fb30edf52', N'mastercard', N'1152', 1, '2026-08-22T22:02:00.000'),
        ((SELECT customer_id FROM @SeedCustomers WHERE customer_reference = N'DEMO-PL-C0181'), N'PROC_A', N'acct_test_proc_a_m05', N'tok_test_pl_50ef1d46a9f4fdf4de300d50d3afee7a', N'mastercard', N'8873', 1, '2026-04-16T08:29:00.000'),
        ((SELECT customer_id FROM @SeedCustomers WHERE customer_reference = N'DEMO-PL-C0182'), N'PROC_A', N'acct_test_proc_a_m04', N'tok_test_pl_bc496cbf74aedd313d18f7a0fb64105d', N'visa', N'3484', 1, '2026-06-06T07:47:00.000'),
        ((SELECT customer_id FROM @SeedCustomers WHERE customer_reference = N'DEMO-PL-C0183'), N'PROC_A', N'acct_test_proc_a_m01', N'tok_test_pl_82f40f1991d416a2ffb8fa2c08249867', N'mastercard', N'0871', 1, '2026-08-07T05:21:00.000'),
        ((SELECT customer_id FROM @SeedCustomers WHERE customer_reference = N'DEMO-PL-C0183'), N'PROC_A', N'acct_test_proc_a_m01', N'tok_test_pl_44bf6196bbf2ad09042593514521c4ba', N'mastercard', N'3585', 0, '2026-08-08T16:21:00.000'),
        ((SELECT customer_id FROM @SeedCustomers WHERE customer_reference = N'DEMO-PL-C0184'), N'PROC_A', N'acct_test_proc_a_m03', N'tok_test_pl_7a8d3fe50bbdf09621bd8e8b4e62c371', N'visa', N'9557', 1, '2026-05-22T03:24:00.000'),
        ((SELECT customer_id FROM @SeedCustomers WHERE customer_reference = N'DEMO-PL-C0185'), N'PROC_A', N'acct_test_proc_a_m01', N'tok_test_pl_64b0fc0ae8428732301867e569cef7bb', N'visa', N'3538', 1, '2026-08-30T11:36:00.000'),
        ((SELECT customer_id FROM @SeedCustomers WHERE customer_reference = N'DEMO-PL-C0186'), N'PROC_A', N'acct_test_proc_a_m05', N'tok_test_pl_bbd08c61f3c1c17132c068db517143ac', N'mastercard', N'4033', 1, '2026-08-30T07:21:00.000'),
        ((SELECT customer_id FROM @SeedCustomers WHERE customer_reference = N'DEMO-PL-C0187'), N'PROC_A', N'acct_test_proc_a_m01', N'tok_test_pl_950ba81ac0eaf3d13cb72ffb12a5ec5c', N'visa', N'6051', 1, '2026-05-10T12:12:00.000'),
        ((SELECT customer_id FROM @SeedCustomers WHERE customer_reference = N'DEMO-PL-C0188'), N'PROC_A', N'acct_test_proc_a_m03', N'tok_test_pl_3b40284ff2e31923efcd52ab77c9d55a', N'visa', N'5049', 1, '2026-10-11T10:25:00.000'),
        ((SELECT customer_id FROM @SeedCustomers WHERE customer_reference = N'DEMO-PL-C0189'), N'PROC_A', N'acct_test_proc_a_m04', N'tok_test_pl_01ba1d6c6ea118a223d560e11d1bf6f2', N'visa', N'0825', 1, '2026-05-05T09:05:00.000'),
        ((SELECT customer_id FROM @SeedCustomers WHERE customer_reference = N'DEMO-PL-C0189'), N'PROC_A', N'acct_test_proc_a_m04', N'tok_test_pl_d4a8de80db56cf04f0297af42774bbad', N'mastercard', N'2961', 1, '2026-05-06T04:05:00.000'),
        ((SELECT customer_id FROM @SeedCustomers WHERE customer_reference = N'DEMO-PL-C0190'), N'PROC_A', N'acct_test_proc_a_m03', N'tok_test_pl_dfa381f4ac75678212fd6adb48bd19d2', N'mastercard', N'9762', 1, '2026-10-16T23:18:00.000'),
        ((SELECT customer_id FROM @SeedCustomers WHERE customer_reference = N'DEMO-PL-C0190'), N'PROC_A', N'acct_test_proc_a_m03', N'tok_test_pl_ec0284bff101a5427ead2e0ff2bdd1c2', N'visa', N'1771', 1, '2026-10-15T17:18:00.000'),
        ((SELECT customer_id FROM @SeedCustomers WHERE customer_reference = N'DEMO-PL-C0191'), N'PROC_A', N'acct_test_proc_a_m01', N'tok_test_pl_08c125fc691eafe3d6288951222d3643', N'mastercard', N'3469', 1, '2026-07-21T05:18:00.000'),
        ((SELECT customer_id FROM @SeedCustomers WHERE customer_reference = N'DEMO-PL-C0192'), N'PROC_A', N'acct_test_proc_a_m03', N'tok_test_pl_c55a31d28db567aa1fcb10ea3c9acb65', N'mastercard', N'4060', 1, '2026-10-08T06:28:00.000'),
        ((SELECT customer_id FROM @SeedCustomers WHERE customer_reference = N'DEMO-PL-C0192'), N'PROC_A', N'acct_test_proc_a_m03', N'tok_test_pl_e9cc7dcd93ab9a55adb14b8c693e806e', N'visa', N'5528', 1, '2026-10-09T23:28:00.000'),
        ((SELECT customer_id FROM @SeedCustomers WHERE customer_reference = N'DEMO-PL-C0193'), N'PROC_A', N'acct_test_proc_a_m04', N'tok_test_pl_cf71492ad7ea185d976df974086afab5', N'mastercard', N'0702', 1, '2026-08-08T00:40:00.000'),
        ((SELECT customer_id FROM @SeedCustomers WHERE customer_reference = N'DEMO-PL-C0193'), N'PROC_A', N'acct_test_proc_a_m04', N'tok_test_pl_6fa0b63206b9960c792796b6cc38f383', N'mastercard', N'3225', 1, '2026-08-07T23:40:00.000'),
        ((SELECT customer_id FROM @SeedCustomers WHERE customer_reference = N'DEMO-PL-C0194'), N'PROC_A', N'acct_test_proc_a_m04', N'tok_test_pl_864e5cb94f6e94f680daf7b101bb94dd', N'mastercard', N'8965', 1, '2026-05-19T00:51:00.000'),
        ((SELECT customer_id FROM @SeedCustomers WHERE customer_reference = N'DEMO-PL-C0195'), N'PROC_A', N'acct_test_proc_a_m01', N'tok_test_pl_3da69e3a98e25ff9897c82b0de969acd', N'mastercard', N'9691', 1, '2026-06-27T14:13:00.000'),
        ((SELECT customer_id FROM @SeedCustomers WHERE customer_reference = N'DEMO-PL-C0195'), N'PROC_A', N'acct_test_proc_a_m01', N'tok_test_pl_a8e7655224b58d2c360b0ba5e5c2b49c', N'mastercard', N'1875', 1, '2026-06-28T10:13:00.000'),
        ((SELECT customer_id FROM @SeedCustomers WHERE customer_reference = N'DEMO-PL-C0196'), N'PROC_A', N'acct_test_proc_a_m04', N'tok_test_pl_ded07da679fcf83bd12741dde5f33013', N'mastercard', N'4415', 1, '2026-10-10T05:59:00.000'),
        ((SELECT customer_id FROM @SeedCustomers WHERE customer_reference = N'DEMO-PL-C0196'), N'PROC_A', N'acct_test_proc_a_m04', N'tok_test_pl_0c36f25868be6408b581a0617ace956c', N'visa', N'0598', 1, '2026-10-10T06:59:00.000'),
        ((SELECT customer_id FROM @SeedCustomers WHERE customer_reference = N'DEMO-PL-C0197'), N'PROC_A', N'acct_test_proc_a_m03', N'tok_test_pl_e2471010669e22658526c61882939d51', N'visa', N'7427', 1, '2026-10-09T01:38:00.000'),
        ((SELECT customer_id FROM @SeedCustomers WHERE customer_reference = N'DEMO-PL-C0198'), N'PROC_A', N'acct_test_proc_a_m04', N'tok_test_pl_268497d1dd5a84b64a2e4ce68c5fc9b2', N'visa', N'8884', 1, '2026-05-17T04:39:00.000'),
        ((SELECT customer_id FROM @SeedCustomers WHERE customer_reference = N'DEMO-PL-C0198'), N'PROC_A', N'acct_test_proc_a_m04', N'tok_test_pl_72266eec0d0ef972d35d634c060386cc', N'visa', N'6701', 1, '2026-05-16T16:39:00.000'),
        ((SELECT customer_id FROM @SeedCustomers WHERE customer_reference = N'DEMO-PL-C0199'), N'PROC_A', N'acct_test_proc_a_m03', N'tok_test_pl_2a9d5a8f7bccf432aa10528a5a9afa13', N'visa', N'6073', 1, '2026-10-01T00:35:00.000'),
        ((SELECT customer_id FROM @SeedCustomers WHERE customer_reference = N'DEMO-PL-C0199'), N'PROC_A', N'acct_test_proc_a_m03', N'tok_test_pl_29d833c5ac73383f0053d89c3db8d5e0', N'visa', N'1966', 1, '2026-10-01T09:35:00.000'),
        ((SELECT customer_id FROM @SeedCustomers WHERE customer_reference = N'DEMO-PL-C0200'), N'PROC_A', N'acct_test_proc_a_m05', N'tok_test_pl_f157c7c38ca090a46ea7bc6c675d1269', N'mastercard', N'6767', 1, '2026-07-27T09:34:00.000');

    -- 4. Payout accounts: eight bank accounts, five active defaults.
    INSERT INTO dbo.merchant_payout_accounts (
        merchant_id, account_holder_name, bank_name, bank_country_code, account_number, iban, swift_code, currency, is_default, is_active, created_at
    )
    OUTPUT inserted.payout_account_id INTO @SeedPayoutAccounts (payout_account_id)
    VALUES
        ((SELECT merchant_id FROM @SeedMerchants WHERE business_name = N'Nile Electronics'), N'Nile Electronics Trading LLC', N'National Bank of Egypt', N'EG', N'005387876460764425', N'EG939901000105387876460764425', NULL, N'EGP', 1, 1, '2025-10-28T13:00:00.000'),
        ((SELECT merchant_id FROM @SeedMerchants WHERE business_name = N'Nile Electronics'), N'Nile Electronics Trading LLC', N'National Bank of Egypt', N'EG', N'002632337279940920', N'EG049901000202632337279940920', NULL, N'EGP', 0, 1, '2025-10-27T13:00:00.000'),
        ((SELECT merchant_id FROM @SeedMerchants WHERE business_name = N'Alex Fashion'), N'Alex Fashion Trading LLC', N'Banque Misr', N'EG', N'004195722369752270', N'EG979902000304195722369752270', NULL, N'EGP', 1, 1, '2025-03-27T12:00:00.000'),
        ((SELECT merchant_id FROM @SeedMerchants WHERE business_name = N'Alex Fashion'), N'Alex Fashion Trading LLC', N'QNB', N'EG', N'001993671187220856', N'EG449903000401993671187220856', NULL, N'EGP', 0, 1, '2025-04-03T12:00:00.000'),
        ((SELECT merchant_id FROM @SeedMerchants WHERE business_name = N'Delta Market'), N'Delta Retail LLC', N'National Bank of Egypt', N'EG', N'006753486952694316', N'EG499901000506753486952694316', NULL, N'EGP', 1, 1, '2025-05-03T04:00:00.000'),
        ((SELECT merchant_id FROM @SeedMerchants WHERE business_name = N'Delta Market'), N'Delta Retail LLC', N'QNB', N'EG', N'003925650693868701', N'EG559903000603925650693868701', NULL, N'EGP', 0, 1, '2025-05-10T04:00:00.000'),
        ((SELECT merchant_id FROM @SeedMerchants WHERE business_name = N'Cairo Home'), N'Cairo Home Supplies LLC', N'CIB', N'EG', N'005597258948509743', N'EG249904000705597258948509743', NULL, N'EGP', 1, 1, '2025-06-16T04:00:00.000'),
        ((SELECT merchant_id FROM @SeedMerchants WHERE business_name = N'Red Sea Sports'), N'Red Sea Sports Trading LLC', N'CIB', N'EG', N'003435443041499812', N'EG359904000803435443041499812', NULL, N'EGP', 1, 1, '2025-11-09T14:00:00.000');

    -- Every payout account in this batch must include an IBAN.
    IF EXISTS (
        SELECT 1
        FROM dbo.merchant_payout_accounts AS a
        JOIN @SeedPayoutAccounts AS s ON s.payout_account_id = a.payout_account_id
        WHERE NULLIF(LTRIM(RTRIM(a.iban)), '') IS NULL
    )
    BEGIN
        THROW 50003, 'A seed payout account is missing its IBAN.', 1;
    END;

    -- Roll back the entire batch if its expected row counts are not met.
    IF (SELECT COUNT(*) FROM @SeedMerchants) <> 5
       OR (SELECT COUNT(*) FROM @SeedCustomers) <> 200
       OR (SELECT COUNT(*) FROM @SeedMethods) <> 278
       OR (SELECT COUNT(*) FROM @SeedPayoutAccounts) <> 8
    BEGIN
        THROW 50002, 'Seed row-count validation failed.', 1;
    END;

    COMMIT TRANSACTION;

    -- These counts describe only rows added by this file.
    SELECT N'merchants' AS table_name, COUNT(*) AS inserted_rows FROM @SeedMerchants
    UNION ALL
    SELECT N'customers', COUNT(*) FROM @SeedCustomers
    UNION ALL
    SELECT N'customer_payment_methods', COUNT(*) FROM @SeedMethods
    UNION ALL
    SELECT N'merchant_payout_accounts', COUNT(*) FROM @SeedPayoutAccounts;

    SELECT m.merchant_id, m.business_name, m.status,
           (SELECT COUNT(*) FROM dbo.customers AS c
            JOIN @SeedCustomers AS sc ON sc.customer_id = c.customer_id
            WHERE c.merchant_id = m.merchant_id) AS seeded_customers,
           (SELECT COUNT(*) FROM dbo.merchant_payout_accounts AS a
            JOIN @SeedPayoutAccounts AS sa ON sa.payout_account_id = a.payout_account_id
            WHERE a.merchant_id = m.merchant_id) AS seeded_payout_accounts
    FROM dbo.merchants AS m
    JOIN @SeedMerchants AS sm ON sm.merchant_id = m.merchant_id
    ORDER BY m.merchant_id;
END TRY
BEGIN CATCH
    IF XACT_STATE() <> 0
        ROLLBACK TRANSACTION;
    THROW;
END CATCH;
