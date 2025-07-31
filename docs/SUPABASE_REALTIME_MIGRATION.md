# Supabase Realtime Migration Guide

## Overview

This document provides a comprehensive guide for migrating the article generation system from WebSocket-based communication to Supabase Realtime with local background tasks. The migration replaces Cloud Tasks dependency with FastAPI BackgroundTasks and database-driven real-time communication.

## Migration Summary

### What Was Implemented

1. **Database Schema Enhancements**
   - Added realtime-specific fields to `generated_articles_state` table
   - Created `process_events` table for event streaming
   - Created `background_tasks` table for task management
   - Added database triggers for automatic realtime publishing
   - Updated Supabase Realtime publications

2. **Backend Changes**
   - New HTTP endpoints for process management (`/generation/start`, `/generation/{id}/user-input`, etc.)
   - Background task manager for article generation workflows
   - Extended generation service with realtime methods
   - Database functions for event publishing and state management

3. **Frontend Changes**
   - Supabase client-side integration
   - Realtime event subscription hooks
   - Updated article generation hook with HTTP API calls
   - Event-driven state management

### Key Benefits

- **No External Dependencies**: Eliminates Cloud Tasks requirement
- **Improved Scalability**: Database-driven background tasks with built-in retry logic
- **Better Reliability**: Automatic reconnection and event ordering
- **Enhanced Monitoring**: Comprehensive event logging and state tracking
- **Backward Compatibility**: Existing WebSocket endpoints remain functional during transition

## Migration Steps

### Phase 1: Database Migration

1. **Apply Database Migration**
   ```bash
   # Run the migration script
   supabase migration apply 20250727000000_supabase_realtime_migration.sql
   ```

2. **Verify Migration**
   ```sql
   -- Check new tables exist
   SELECT table_name FROM information_schema.tables 
   WHERE table_schema = 'public' 
   AND table_name IN ('process_events', 'background_tasks', 'task_dependencies');

   -- Check new columns in generated_articles_state
   SELECT column_name FROM information_schema.columns 
   WHERE table_name = 'generated_articles_state' 
   AND column_name IN ('realtime_channel', 'executing_step', 'background_task_id');

   -- Check realtime publication
   SELECT tablename FROM pg_publication_tables 
   WHERE pubname = 'supabase_realtime';
   ```

### Phase 2: Backend Deployment

1. **Deploy Backend Changes**
   - Deploy updated `endpoints.py` with new HTTP endpoints
   - Deploy `background_task_manager.py` for task management
   - Deploy updated `generation_service.py` with realtime methods

2. **Verify Backend Endpoints**
   ```bash
   # Test new endpoint availability
   curl -X POST /api/articles/generation/start \
     -H "Content-Type: application/json" \
     -H "Authorization: Bearer <token>" \
     -d '{"initial_keywords": ["test"]}'
   ```

### Phase 3: Frontend Integration

1. **Deploy Frontend Changes**
   - Deploy `supabase-client.ts` for client-side Supabase integration
   - Deploy `useSupabaseRealtime.ts` hook for realtime subscriptions
   - Deploy `useArticleGenerationRealtime.ts` for article generation

2. **Update Components**
   - Replace existing `useArticleGeneration` with `useArticleGenerationRealtime`
   - Update article generation components to use new hook
   - Test real-time event handling

### Phase 4: Testing and Validation

1. **End-to-End Testing** (see Testing Guide below)
2. **Performance Monitoring**
3. **Gradual Rollout** with feature flags
4. **WebSocket Deprecation** (after successful validation)

## Database Schema Reference

### New Tables

#### `process_events`
```sql
CREATE TABLE process_events (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  process_id UUID NOT NULL REFERENCES generated_articles_state(id),
  event_type TEXT NOT NULL,
  event_data JSONB NOT NULL DEFAULT '{}'::jsonb,
  event_sequence INTEGER NOT NULL,
  created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
  published_at TIMESTAMP WITH TIME ZONE,
  acknowledged_by TEXT[] DEFAULT '{}',
  -- Additional metadata fields...
);
```

#### `background_tasks`
```sql
CREATE TABLE background_tasks (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  process_id UUID NOT NULL REFERENCES generated_articles_state(id),
  task_type TEXT NOT NULL,
  task_data JSONB NOT NULL DEFAULT '{}'::jsonb,
  status TEXT DEFAULT 'pending',
  priority INTEGER DEFAULT 5,
  -- Scheduling and retry fields...
);
```

### Enhanced Fields in `generated_articles_state`

- `realtime_channel`: Supabase Realtime channel name
- `executing_step`: Currently executing step
- `background_task_id`: Associated background task ID
- `user_input_timeout`: When user input request expires
- `interaction_history`: History of user interactions

## API Reference

### New HTTP Endpoints

#### Start Generation Process
```http
POST /api/articles/generation/start
Content-Type: application/json
Authorization: Bearer <token>

{
  "initial_keywords": ["keyword1", "keyword2"],
  "target_age_group": "30代",
  "persona_type": "主婦",
  "image_mode": false
}
```

Response:
```json
{
  "process_id": "uuid",
  "realtime_channel": "process_uuid",
  "status": "started",
  "subscription_info": {
    "table": "process_events",
    "filter": "process_id=eq.uuid"
  }
}
```

#### Submit User Input
```http
POST /api/articles/generation/{process_id}/user-input
Content-Type: application/json
Authorization: Bearer <token>

{
  "response_type": "select_persona",
  "payload": {
    "selected_id": 0
  }
}
```

#### Process Management
```http
POST /api/articles/generation/{process_id}/pause
POST /api/articles/generation/{process_id}/resume
DELETE /api/articles/generation/{process_id}
```

#### Event Retrieval
```http
GET /api/articles/generation/{process_id}/events?since_sequence=10&limit=50
```

## Frontend Integration Guide

### Basic Usage

```typescript
import { useArticleGenerationRealtime } from '@/hooks/useArticleGenerationRealtime';

function ArticleGenerationPage() {
  const {
    state,
    isConnected,
    startArticleGeneration,
    selectPersona,
    selectTheme,
    approvePlan,
    approveOutline,
  } = useArticleGenerationRealtime({
    processId: router.query.processId as string,
    userId: user?.id,
  });

  const handleStart = async (formData) => {
    const result = await startArticleGeneration(formData);
    router.push(`/generation/${result.process_id}`);
  };

  const handlePersonaSelect = async (personaId: number) => {
    await selectPersona(personaId);
  };

  return (
    <div>
      <div>Status: {isConnected ? 'Connected' : 'Disconnected'}</div>
      <div>Current Step: {state.currentStep}</div>
      
      {state.isWaitingForInput && state.inputType === 'select_persona' && (
        <PersonaSelection 
          personas={state.personas}
          onSelect={handlePersonaSelect}
        />
      )}
      
      {/* Other UI components... */}
    </div>
  );
}
```

### Event Handling

```typescript
const { isConnected } = useSupabaseRealtime({
  processId,
  userId,
  onEvent: (event) => {
    console.log('Received event:', event.event_type, event.event_data);
    
    switch (event.event_type) {
      case 'step_started':
        setCurrentStep(event.event_data.step_name);
        break;
      case 'user_input_required':
        setWaitingForInput(true);
        setInputType(event.event_data.input_type);
        break;
      // Handle other event types...
    }
  },
  onError: (error) => {
    console.error('Realtime error:', error);
  },
});
```

## Testing Guide

### 1. Database Migration Testing

```sql
-- Test database functions
SELECT create_process_event(
  'test-process-id'::uuid,
  'test_event',
  '{"test": "data"}'::jsonb
);

-- Test triggers
UPDATE generated_articles_state 
SET status = 'in_progress' 
WHERE id = 'test-process-id';

-- Verify events were created
SELECT * FROM process_events WHERE process_id = 'test-process-id';
```

### 2. Backend API Testing

```bash
# Test generation start
curl -X POST http://localhost:8000/api/articles/generation/start \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $TOKEN" \
  -d '{
    "initial_keywords": ["test", "article"],
    "target_age_group": "30代",
    "persona_type": "主婦"
  }'

# Test user input
curl -X POST http://localhost:8000/api/articles/generation/$PROCESS_ID/user-input \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $TOKEN" \
  -d '{
    "response_type": "select_persona",
    "payload": {"selected_id": 0}
  }'

# Test process control
curl -X POST http://localhost:8000/api/articles/generation/$PROCESS_ID/pause \
  -H "Authorization: Bearer $TOKEN"

curl -X DELETE http://localhost:8000/api/articles/generation/$PROCESS_ID \
  -H "Authorization: Bearer $TOKEN"
```

### 3. Realtime Subscription Testing

```typescript
// Test realtime connection
import { supabase } from '@/libs/supabase/supabase-client';

const testRealtimeConnection = async () => {
  const processId = 'test-process-id';
  
  const channel = supabase
    .channel(`process_events:process_id=eq.${processId}`)
    .on('postgres_changes', 
      {
        event: 'INSERT',
        schema: 'public',
        table: 'process_events',
        filter: `process_id=eq.${processId}`,
      },
      (payload) => {
        console.log('Received realtime event:', payload);
      }
    )
    .subscribe((status) => {
      console.log('Subscription status:', status);
    });
  
  // Test event creation via API
  await fetch(`/api/articles/generation/${processId}/test-event`, {
    method: 'POST',
  });
  
  // Cleanup
  setTimeout(() => {
    channel.unsubscribe();
  }, 5000);
};
```

### 4. End-to-End Testing Scenarios

#### Scenario 1: Complete Article Generation Flow
1. Start new generation process
2. Verify realtime connection established
3. Monitor step progression events
4. Handle user input prompts (persona, theme, plan, outline)
5. Verify final article completion
6. Check article saved to database

#### Scenario 2: Process Recovery
1. Start generation process
2. Simulate disconnection (close browser tab)
3. Reconnect and verify process resumption
4. Check missed events are fetched
5. Continue from current step

#### Scenario 3: Error Handling
1. Start generation with invalid parameters
2. Verify error events are published
3. Test process pause/resume functionality
4. Test process cancellation

#### Scenario 4: Concurrent Processes
1. Start multiple generation processes
2. Verify events are isolated per process
3. Test user input for different processes
4. Check database consistency

### 5. Performance Testing

```bash
# Test concurrent connections
for i in {1..10}; do
  curl -X POST http://localhost:8000/api/articles/generation/start \
    -H "Content-Type: application/json" \
    -H "Authorization: Bearer $TOKEN" \
    -d '{"initial_keywords": ["test'$i'"]}' &
done
wait

# Monitor database performance
SELECT 
  table_name,
  pg_size_pretty(pg_total_relation_size(schemaname||'.'||tablename)) as size
FROM pg_tables 
WHERE schemaname = 'public' 
AND tablename IN ('process_events', 'background_tasks', 'generated_articles_state');
```

## Monitoring and Observability

### Key Metrics to Monitor

1. **Database Performance**
   - Process events table size and growth rate
   - Background tasks queue length
   - Query performance on indexed columns

2. **Realtime Performance**
   - Connection success rate
   - Event delivery latency
   - Reconnection frequency

3. **Application Performance**
   - Background task execution time
   - Step completion rates
   - Error rates by step type

### Monitoring Queries

```sql
-- Active processes
SELECT status, COUNT(*) 
FROM generated_articles_state 
GROUP BY status;

-- Recent events
SELECT event_type, COUNT(*) 
FROM process_events 
WHERE created_at > NOW() - INTERVAL '1 hour'
GROUP BY event_type;

-- Task queue health
SELECT status, priority, COUNT(*), AVG(EXTRACT(EPOCH FROM (NOW() - created_at)))
FROM background_tasks 
WHERE created_at > NOW() - INTERVAL '1 hour'
GROUP BY status, priority;

-- Failed processes
SELECT process_id, error_message, updated_at
FROM generated_articles_state 
WHERE status = 'error' 
ORDER BY updated_at DESC 
LIMIT 10;
```

## Troubleshooting

### Common Issues

1. **Realtime Connection Failures**
   - Check Supabase project settings
   - Verify RLS policies are correct
   - Check network connectivity

2. **Missing Events**
   - Verify database triggers are active
   - Check event sequence numbers
   - Use missed events fetch mechanism

3. **Background Task Failures**
   - Check task status in `background_tasks` table
   - Review error messages and retry counts
   - Verify database connectivity

4. **Process Recovery Issues**
   - Check process state consistency
   - Verify context serialization/deserialization
   - Review step transition logic

### Debug Commands

```bash
# Check Supabase realtime status
curl https://your-project.supabase.co/realtime/v1/health

# Test database connectivity
psql "postgresql://..." -c "SELECT NOW();"

# Check background task queue
curl -X GET http://localhost:8000/api/internal/background-tasks/status
```

## Rollback Plan

If issues arise during migration:

1. **Immediate Rollback**
   - Switch feature flag to use WebSocket endpoints
   - Stop new realtime-based processes
   - Allow existing WebSocket processes to complete

2. **Database Rollback**
   ```sql
   -- Disable triggers (if needed)
   ALTER TABLE generated_articles_state DISABLE TRIGGER trigger_publish_process_event;
   
   -- Drop new tables (if required)
   DROP TABLE IF EXISTS process_events CASCADE;
   DROP TABLE IF EXISTS background_tasks CASCADE;
   ```

3. **Code Rollback**
   - Revert backend endpoints to previous version
   - Revert frontend hooks to WebSocket version
   - Monitor for residual issues

## Success Criteria

The migration is considered successful when:

1. ✅ All database migrations applied successfully
2. ✅ New HTTP endpoints are functional
3. ✅ Realtime events are received correctly
4. ✅ Background tasks execute without errors
5. ✅ End-to-end article generation works
6. ✅ Process recovery functions correctly
7. ✅ Performance meets or exceeds WebSocket version
8. ✅ No data loss during transition
9. ✅ Error rates remain within acceptable limits
10. ✅ User experience is maintained or improved

## Next Steps

After successful migration:

1. **Monitor Performance** for 1-2 weeks
2. **Gather User Feedback** on new experience
3. **Optimize Database Queries** based on usage patterns
4. **Remove WebSocket Dependencies** and clean up code
5. **Document Lessons Learned** for future migrations
6. **Consider Additional Features** enabled by new architecture

---

**Migration completed on**: [Date to be filled]
**Signed off by**: [Team lead to sign off]