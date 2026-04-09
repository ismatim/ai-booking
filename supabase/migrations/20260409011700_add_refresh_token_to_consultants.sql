-- 1. Add the column to store the Google Refresh Token
ALTER TABLE consultants 
ADD COLUMN google_refresh_token TEXT;

-- 2. Add a description for the dashboard
COMMENT ON COLUMN consultants.google_refresh_token IS 'The OAuth2 refresh token used to generate new access tokens for Google Calendar.';

-- 3. Safety: Ensure this column isn't accidentally leaked to the frontend
-- If you use 'SELECT *' in your API, you might want to create a specific view 
-- that excludes this token, but since your backend uses the service_role key, 
-- it will always have access.
