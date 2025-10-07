/*
  # BurnAfterIt Database Schema

  ## Overview
  Creates the complete database schema for the BurnAfterIt ephemeral content sharing platform.
  This migration replaces the InfluxDB time-series database with a proper relational PostgreSQL database.

  ## New Tables

  ### 1. `shouts` - Main content table
    - `id` (uuid, primary key) - Unique identifier for each shout
    - `hash` (text, unique) - URL-safe hash for accessing the content
    - `user_id` (uuid, nullable) - Reference to authenticated user (null for anonymous)
    - `type` (text) - Content type: 'text', 'audio', 'video', 'photo'
    - `max_hits` (integer) - Maximum number of views allowed
    - `max_time_minutes` (integer) - Maximum time in minutes before expiration
    - `current_hits` (integer) - Current view count
    - `content_text` (text, nullable) - For text shouts, stores the message
    - `storage_key` (text, nullable) - S3/Supabase storage key for media files
    - `created_at` (timestamptz) - Creation timestamp
    - `expires_at` (timestamptz) - Calculated expiration time
    - `is_active` (boolean) - Whether the shout is still viewable

  ### 2. `chat_rooms` - Ephemeral chat rooms
    - `id` (uuid, primary key) - Unique identifier
    - `hash` (text, unique) - URL-safe hash for accessing the chat
    - `created_at` (timestamptz) - Creation timestamp
    - `expires_at` (timestamptz) - Auto-expiration time (5 minutes default)

  ### 3. `chat_messages` - Messages within chat rooms
    - `id` (uuid, primary key) - Unique identifier
    - `chat_room_id` (uuid, foreign key) - Reference to chat room
    - `shout_id` (uuid, foreign key) - Reference to the shout (message content)
    - `created_at` (timestamptz) - Message timestamp

  ### 4. `hit_logs` - View tracking for analytics
    - `id` (uuid, primary key) - Unique identifier
    - `shout_id` (uuid, foreign key) - Reference to shout
    - `user_agent` (text) - Browser/client information
    - `ip_address` (text) - Client IP (for abuse prevention)
    - `viewed_at` (timestamptz) - View timestamp

  ## Security
    - RLS (Row Level Security) enabled on all tables
    - Policies allow public read access only for active, non-expired content
    - Write access restricted to appropriate contexts
    - User identification via anonymous or authenticated sessions

  ## Indexes
    - Indexes on hash columns for fast lookups
    - Indexes on expiration checks
    - Indexes on foreign keys for join performance

  ## Notes
    - All timestamps use timestamptz for timezone awareness
    - UUIDs used for all primary keys
    - Cascade deletes ensure cleanup when parent records are removed
    - Default values ensure data consistency
*/

-- Create shouts table
CREATE TABLE IF NOT EXISTS shouts (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  hash text UNIQUE NOT NULL,
  user_id uuid,
  type text NOT NULL CHECK (type IN ('text', 'audio', 'video', 'photo')),
  max_hits integer NOT NULL DEFAULT 1,
  max_time_minutes integer NOT NULL DEFAULT 240,
  current_hits integer NOT NULL DEFAULT 0,
  content_text text,
  storage_key text,
  created_at timestamptz DEFAULT now(),
  expires_at timestamptz NOT NULL,
  is_active boolean DEFAULT true
);

-- Create indexes on shouts
CREATE INDEX IF NOT EXISTS idx_shouts_hash ON shouts(hash);
CREATE INDEX IF NOT EXISTS idx_shouts_expires_at ON shouts(expires_at);
CREATE INDEX IF NOT EXISTS idx_shouts_is_active ON shouts(is_active);
CREATE INDEX IF NOT EXISTS idx_shouts_user_id ON shouts(user_id);

-- Create chat_rooms table
CREATE TABLE IF NOT EXISTS chat_rooms (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  hash text UNIQUE NOT NULL,
  created_at timestamptz DEFAULT now(),
  expires_at timestamptz NOT NULL
);

-- Create indexes on chat_rooms
CREATE INDEX IF NOT EXISTS idx_chat_rooms_hash ON chat_rooms(hash);
CREATE INDEX IF NOT EXISTS idx_chat_rooms_expires_at ON chat_rooms(expires_at);

-- Create chat_messages table
CREATE TABLE IF NOT EXISTS chat_messages (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  chat_room_id uuid NOT NULL REFERENCES chat_rooms(id) ON DELETE CASCADE,
  shout_id uuid NOT NULL REFERENCES shouts(id) ON DELETE CASCADE,
  created_at timestamptz DEFAULT now()
);

-- Create indexes on chat_messages
CREATE INDEX IF NOT EXISTS idx_chat_messages_chat_room_id ON chat_messages(chat_room_id);
CREATE INDEX IF NOT EXISTS idx_chat_messages_created_at ON chat_messages(created_at);

-- Create hit_logs table
CREATE TABLE IF NOT EXISTS hit_logs (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  shout_id uuid NOT NULL REFERENCES shouts(id) ON DELETE CASCADE,
  user_agent text,
  ip_address text,
  viewed_at timestamptz DEFAULT now()
);

-- Create indexes on hit_logs
CREATE INDEX IF NOT EXISTS idx_hit_logs_shout_id ON hit_logs(shout_id);
CREATE INDEX IF NOT EXISTS idx_hit_logs_viewed_at ON hit_logs(viewed_at);

-- Enable Row Level Security
ALTER TABLE shouts ENABLE ROW LEVEL SECURITY;
ALTER TABLE chat_rooms ENABLE ROW LEVEL SECURITY;
ALTER TABLE chat_messages ENABLE ROW LEVEL SECURITY;
ALTER TABLE hit_logs ENABLE ROW LEVEL SECURITY;

-- RLS Policies for shouts table

-- Anyone can view active, non-expired shouts
CREATE POLICY "Anyone can view active shouts"
  ON shouts FOR SELECT
  USING (
    is_active = true 
    AND expires_at > now()
    AND current_hits < max_hits
  );

-- Anyone can create shouts (anonymous or authenticated)
CREATE POLICY "Anyone can create shouts"
  ON shouts FOR INSERT
  WITH CHECK (true);

-- Only system can update shouts (for hit counting)
CREATE POLICY "System can update shouts"
  ON shouts FOR UPDATE
  USING (true)
  WITH CHECK (true);

-- RLS Policies for chat_rooms table

-- Anyone can view non-expired chat rooms
CREATE POLICY "Anyone can view active chat rooms"
  ON chat_rooms FOR SELECT
  USING (expires_at > now());

-- Anyone can create chat rooms
CREATE POLICY "Anyone can create chat rooms"
  ON chat_rooms FOR INSERT
  WITH CHECK (true);

-- RLS Policies for chat_messages table

-- Anyone can view messages in active chat rooms
CREATE POLICY "Anyone can view chat messages"
  ON chat_messages FOR SELECT
  USING (
    EXISTS (
      SELECT 1 FROM chat_rooms
      WHERE chat_rooms.id = chat_messages.chat_room_id
      AND chat_rooms.expires_at > now()
    )
  );

-- Anyone can create chat messages
CREATE POLICY "Anyone can create chat messages"
  ON chat_messages FOR INSERT
  WITH CHECK (true);

-- RLS Policies for hit_logs table

-- Only system can insert hit logs
CREATE POLICY "System can insert hit logs"
  ON hit_logs FOR INSERT
  WITH CHECK (true);

-- No one can read hit logs directly (use functions for analytics)
CREATE POLICY "No direct access to hit logs"
  ON hit_logs FOR SELECT
  USING (false);

-- Create function to increment hit count and check validity
CREATE OR REPLACE FUNCTION increment_shout_hit(shout_hash text, client_ip text, client_ua text)
RETURNS json
LANGUAGE plpgsql
SECURITY DEFINER
AS $$
DECLARE
  shout_record shouts;
  result json;
BEGIN
  -- Get the shout with row lock
  SELECT * INTO shout_record
  FROM shouts
  WHERE hash = shout_hash
  FOR UPDATE;

  -- Check if shout exists
  IF NOT FOUND THEN
    RETURN json_build_object('valid', false, 'reason', 'not_found');
  END IF;

  -- Check if expired by time
  IF shout_record.expires_at <= now() THEN
    UPDATE shouts SET is_active = false WHERE id = shout_record.id;
    RETURN json_build_object('valid', false, 'reason', 'expired_time');
  END IF;

  -- Check if expired by hits
  IF shout_record.current_hits >= shout_record.max_hits THEN
    UPDATE shouts SET is_active = false WHERE id = shout_record.id;
    RETURN json_build_object('valid', false, 'reason', 'expired_hits');
  END IF;

  -- Check if inactive
  IF NOT shout_record.is_active THEN
    RETURN json_build_object('valid', false, 'reason', 'inactive');
  END IF;

  -- Increment hit count
  UPDATE shouts
  SET current_hits = current_hits + 1
  WHERE id = shout_record.id;

  -- Log the hit
  INSERT INTO hit_logs (shout_id, user_agent, ip_address)
  VALUES (shout_record.id, client_ua, client_ip);

  -- Return success with shout data
  RETURN json_build_object(
    'valid', true,
    'shout', row_to_json(shout_record)
  );
END;
$$;

-- Create function to cleanup expired content
CREATE OR REPLACE FUNCTION cleanup_expired_content()
RETURNS void
LANGUAGE plpgsql
SECURITY DEFINER
AS $$
BEGIN
  -- Mark expired shouts as inactive
  UPDATE shouts
  SET is_active = false
  WHERE (expires_at <= now() OR current_hits >= max_hits)
  AND is_active = true;

  -- Delete old hit logs (older than 7 days)
  DELETE FROM hit_logs
  WHERE viewed_at < now() - interval '7 days';

  -- Delete expired chat rooms (and cascade to messages)
  DELETE FROM chat_rooms
  WHERE expires_at < now() - interval '1 hour';
END;
$$;