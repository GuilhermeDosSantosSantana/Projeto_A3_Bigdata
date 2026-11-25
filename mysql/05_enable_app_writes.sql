USE giro_a3;
-- Existing large installations need to release referring FKs before changing IDs.
ALTER TABLE batch DROP FOREIGN KEY fk_batch_product;
ALTER TABLE sale DROP FOREIGN KEY fk_sale_product;
ALTER TABLE stock_event DROP FOREIGN KEY fk_event_batch;
ALTER TABLE stock_event DROP FOREIGN KEY fk_event_sale;
ALTER TABLE product MODIFY id BIGINT NOT NULL AUTO_INCREMENT;
ALTER TABLE batch MODIFY id BIGINT NOT NULL AUTO_INCREMENT;
ALTER TABLE sale MODIFY id BIGINT NOT NULL AUTO_INCREMENT;
ALTER TABLE stock_event MODIFY id BIGINT NOT NULL AUTO_INCREMENT;
ALTER TABLE batch ADD CONSTRAINT fk_batch_product FOREIGN KEY (product_id) REFERENCES product(id);
ALTER TABLE sale ADD CONSTRAINT fk_sale_product FOREIGN KEY (product_id) REFERENCES product(id);
ALTER TABLE stock_event ADD CONSTRAINT fk_event_batch FOREIGN KEY (batch_id) REFERENCES batch(id);
ALTER TABLE stock_event ADD CONSTRAINT fk_event_sale FOREIGN KEY (sale_id) REFERENCES sale(id);
