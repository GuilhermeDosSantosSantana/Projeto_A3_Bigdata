USE giro_a3;
DELIMITER //
CREATE TRIGGER trg_event_validate BEFORE INSERT ON stock_event FOR EACH ROW
BEGIN
  DECLARE received INT;
  DECLARE used INT;
  DECLARE batch_product BIGINT;
  DECLARE sale_product BIGINT;

  -- Serialize writes to one batch before verifying its available quantity.
  SELECT quantity_received, product_id INTO received, batch_product
  FROM batch WHERE id = NEW.batch_id FOR UPDATE;

  SELECT COALESCE(SUM(quantity), 0) INTO used
  FROM stock_event WHERE batch_id = NEW.batch_id;

  IF NEW.quantity + used > received THEN
    SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'batch stock cannot be negative';
  END IF;

  IF NEW.kind = 'SALE' THEN
    SELECT product_id INTO sale_product FROM sale WHERE id = NEW.sale_id;
    IF sale_product <> batch_product THEN
      SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'sale and batch product mismatch';
    END IF;
  END IF;
END//
DELIMITER ;
