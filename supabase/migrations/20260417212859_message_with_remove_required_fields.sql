-- Make the old columns optional so LangChain's automatic tool can skip them
ALTER TABLE messages ALTER COLUMN role DROP NOT NULL;
ALTER TABLE messages ALTER COLUMN content DROP NOT NULL;
