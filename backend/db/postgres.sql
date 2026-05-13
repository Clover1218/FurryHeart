/*
 Navicat Premium Data Transfer

 Source Server         : postgreSQL18test
 Source Server Type    : PostgreSQL
 Source Server Version : 180003 (180003)
 Source Host           : localhost:5432
 Source Catalog        : heartbottest
 Source Schema         : public

 Target Server Type    : PostgreSQL
 Target Server Version : 180003 (180003)
 File Encoding         : 65001

 Date: 13/05/2026 18:42:47
*/


CREATE EXTENSION IF NOT EXISTS vector;
-- ----------------------------
-- Table structure for chat_history
-- ----------------------------
DROP TABLE IF EXISTS "chat_history";
CREATE TABLE "chat_history" (
  "id" uuid NOT NULL,
  "user_id" text COLLATE "pg_catalog"."default" NOT NULL,
  "session_id" text COLLATE "pg_catalog"."default" NOT NULL,
  "role" text COLLATE "pg_catalog"."default" NOT NULL,
  "content" text COLLATE "pg_catalog"."default" NOT NULL,
  "created_at" timestamp(6) DEFAULT CURRENT_TIMESTAMP
)
;

-- ----------------------------
-- Table structure for config_schema
-- ----------------------------
DROP TABLE IF EXISTS "config_schema";
CREATE TABLE "config_schema" (
  "key" text COLLATE "pg_catalog"."default" NOT NULL,
  "type" text COLLATE "pg_catalog"."default",
  "default_value" jsonb,
  "options" jsonb,
  "description" text COLLATE "pg_catalog"."default"
)
;

-- ----------------------------
-- Table structure for memories
-- ----------------------------
DROP TABLE IF EXISTS "memories";
CREATE TABLE "memories" (
  "id" uuid NOT NULL,
  "user_id" text COLLATE "pg_catalog"."default" NOT NULL,
  "device_id" text COLLATE "pg_catalog"."default",
  "content" text COLLATE "pg_catalog"."default" NOT NULL,
  "type" text COLLATE "pg_catalog"."default" NOT NULL,
  "source_memory_ids" jsonb,
  "tags" jsonb,
  "embedding" "public"."vector",
  "emotion" text COLLATE "pg_catalog"."default",
  "emotion_intensity" float8,
  "importance" float8,
  "created_at" timestamptz(6) DEFAULT now(),
  "last_used_at" timestamptz(6),
  "access_count" int4 DEFAULT 0,
  "is_active" bool DEFAULT true,
  "emotion_confidence" float8
)
;

-- ----------------------------
-- Table structure for memory_edges
-- ----------------------------
DROP TABLE IF EXISTS "memory_edges";
CREATE TABLE "memory_edges" (
  "id" uuid NOT NULL DEFAULT gen_random_uuid(),
  "source_node_id" uuid NOT NULL,
  "target_node_id" uuid NOT NULL,
  "relation_type" text COLLATE "pg_catalog"."default" NOT NULL,
  "strength" float8 DEFAULT 0.5,
  "properties" jsonb DEFAULT '{}'::jsonb,
  "created_at" timestamptz(6) DEFAULT now(),
  "updated_at" timestamptz(6) DEFAULT now()
)
;

-- ----------------------------
-- Table structure for memory_nodes
-- ----------------------------
DROP TABLE IF EXISTS "memory_nodes";
CREATE TABLE "memory_nodes" (
  "id" uuid NOT NULL DEFAULT gen_random_uuid(),
  "user_id" text COLLATE "pg_catalog"."default",
  "name" text COLLATE "pg_catalog"."default" NOT NULL,
  "type" text COLLATE "pg_catalog"."default" NOT NULL,
  "properties" jsonb DEFAULT '{}'::jsonb,
  "created_at" timestamptz(6) DEFAULT now(),
  "updated_at" timestamptz(6) DEFAULT now(),
  "memory_items" json
)
;

-- ----------------------------
-- Table structure for sessions
-- ----------------------------
DROP TABLE IF EXISTS "sessions";
CREATE TABLE "sessions" (
  "id" uuid NOT NULL DEFAULT gen_random_uuid(),
  "user_id" text COLLATE "pg_catalog"."default" NOT NULL,
  "device_id" text COLLATE "pg_catalog"."default",
  "session_id" text COLLATE "pg_catalog"."default" NOT NULL,
  "start_time" timestamptz(6) NOT NULL,
  "last_active" timestamptz(6) NOT NULL,
  "turn_count" int4 DEFAULT 0,
  "state" text COLLATE "pg_catalog"."default" DEFAULT 'IDLE'::text,
  "emotion" text COLLATE "pg_catalog"."default",
  "memory_extracted" bool DEFAULT false,
  "created_at" timestamptz(6) DEFAULT now(),
  "updated_at" timestamptz(6) DEFAULT now()
)
;

-- ----------------------------
-- Table structure for system_config
-- ----------------------------
DROP TABLE IF EXISTS "system_config";
CREATE TABLE "system_config" (
  "key" text COLLATE "pg_catalog"."default" NOT NULL,
  "value" jsonb,
  "updated_at" timestamp(6) DEFAULT now()
)
;

-- ----------------------------
-- Table structure for user_config
-- ----------------------------
DROP TABLE IF EXISTS "user_config";
CREATE TABLE "user_config" (
  "user_id" text COLLATE "pg_catalog"."default" NOT NULL,
  "key" text COLLATE "pg_catalog"."default" NOT NULL,
  "value" jsonb,
  "updated_at" timestamp(6)
)
;

-- ----------------------------
-- Table structure for user_info
-- ----------------------------
DROP TABLE IF EXISTS "user_info";
CREATE TABLE "user_info" (
  "user_id" uuid NOT NULL,
  "open_id" varchar(64) COLLATE "pg_catalog"."default" NOT NULL,
  "nickname" varchar(64) COLLATE "pg_catalog"."default",
  "avatar_url" varchar(255) COLLATE "pg_catalog"."default",
  "created_at" timestamptz(6) DEFAULT CURRENT_TIMESTAMP,
  "updated_at" timestamptz(6) DEFAULT CURRENT_TIMESTAMP
)
;


-- ----------------------------
-- Indexes structure for table chat_history
-- ----------------------------
CREATE INDEX "idx_user_session_time" ON "chat_history" USING btree (
  "user_id" COLLATE "pg_catalog"."default" "pg_catalog"."text_ops" ASC NULLS LAST,
  "session_id" COLLATE "pg_catalog"."default" "pg_catalog"."text_ops" ASC NULLS LAST,
  "created_at" "pg_catalog"."timestamp_ops" DESC NULLS FIRST
);

-- ----------------------------
-- Primary Key structure for table chat_history
-- ----------------------------
ALTER TABLE "chat_history" ADD CONSTRAINT "chat_history_pkey" PRIMARY KEY ("id");

-- ----------------------------
-- Primary Key structure for table config_schema
-- ----------------------------
ALTER TABLE "config_schema" ADD CONSTRAINT "config_schema_pkey" PRIMARY KEY ("key");

-- ----------------------------
-- Checks structure for table memories
-- ----------------------------
ALTER TABLE "memories" ADD CONSTRAINT "memories_emotion_intensity_check" CHECK (emotion_intensity >= 0::double precision AND emotion_intensity <= 1::double precision);
ALTER TABLE "memories" ADD CONSTRAINT "memories_importance_check" CHECK (importance >= 0::double precision AND importance <= 1::double precision);
ALTER TABLE "memories" ADD CONSTRAINT "memories_type_check" CHECK (type = ANY (ARRAY['event'::text, 'insight'::text]));

-- ----------------------------
-- Primary Key structure for table memories
-- ----------------------------
ALTER TABLE "memories" ADD CONSTRAINT "memories_pkey" PRIMARY KEY ("id");

-- ----------------------------
-- Checks structure for table memory_edges
-- ----------------------------
ALTER TABLE "memory_edges" ADD CONSTRAINT "memory_edges_strength_check" CHECK (strength >= 0::double precision AND strength <= 1::double precision);

-- ----------------------------
-- Primary Key structure for table memory_edges
-- ----------------------------
ALTER TABLE "memory_edges" ADD CONSTRAINT "memory_edges_pkey" PRIMARY KEY ("id");

-- ----------------------------
-- Primary Key structure for table memory_nodes
-- ----------------------------
ALTER TABLE "memory_nodes" ADD CONSTRAINT "memory_nodes_pkey" PRIMARY KEY ("id");

-- ----------------------------
-- Indexes structure for table sessions
-- ----------------------------
CREATE INDEX "idx_sessions_last_active" ON "sessions" USING btree (
  "last_active" "pg_catalog"."timestamptz_ops" ASC NULLS LAST
);
CREATE INDEX "idx_sessions_state" ON "sessions" USING btree (
  "state" COLLATE "pg_catalog"."default" "pg_catalog"."text_ops" ASC NULLS LAST
);
CREATE INDEX "idx_sessions_user_id" ON "sessions" USING btree (
  "user_id" COLLATE "pg_catalog"."default" "pg_catalog"."text_ops" ASC NULLS LAST
);

-- ----------------------------
-- Uniques structure for table sessions
-- ----------------------------
ALTER TABLE "sessions" ADD CONSTRAINT "sessions_user_id_session_id_key" UNIQUE ("user_id", "session_id");

-- ----------------------------
-- Primary Key structure for table sessions
-- ----------------------------
ALTER TABLE "sessions" ADD CONSTRAINT "sessions_pkey" PRIMARY KEY ("id");

-- ----------------------------
-- Primary Key structure for table system_config
-- ----------------------------
ALTER TABLE "system_config" ADD CONSTRAINT "system_config_pkey" PRIMARY KEY ("key");

-- ----------------------------
-- Primary Key structure for table user_config
-- ----------------------------
ALTER TABLE "user_config" ADD CONSTRAINT "user_config_pkey" PRIMARY KEY ("user_id", "key");

-- ----------------------------
-- Uniques structure for table user_info
-- ----------------------------
ALTER TABLE "user_info" ADD CONSTRAINT "user_info_openid_key" UNIQUE ("open_id");

-- ----------------------------
-- Foreign Keys structure for table memory_edges
-- ----------------------------
ALTER TABLE "memory_edges" ADD CONSTRAINT "memory_edges_source_node_id_fkey" FOREIGN KEY ("source_node_id") REFERENCES "memory_nodes" ("id") ON DELETE CASCADE ON UPDATE NO ACTION;
ALTER TABLE "memory_edges" ADD CONSTRAINT "memory_edges_target_node_id_fkey" FOREIGN KEY ("target_node_id") REFERENCES "memory_nodes" ("id") ON DELETE CASCADE ON UPDATE NO ACTION;



INSERT INTO "public"."config_schema" VALUES ('prompt.scenes', 'list', '[{"condition": "感知到用户压力大", "scene_name": "工作", "response_text": "你已经很棒啦~~~~~~~~~~~~~~~~~~"}, {"condition": "用户感到被催婚，很烦", "scene_name": "家庭催婚", "response_text": "老子想活成什么样就什么样"}]', NULL, '场景设置');
INSERT INTO "public"."config_schema" VALUES ('prompt.system_base', 'string', '{"text": "你是绒绒，给用户提供情绪价值"}', NULL, '基础人格');
