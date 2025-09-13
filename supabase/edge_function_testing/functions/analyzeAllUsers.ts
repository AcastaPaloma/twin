import { createClient } from '@supabase/supabase-js';
import { CohereClientV2 } from 'cohere-ai';



// Load from environment variables
const SUPABASE_URL = process.env.NEXT_PUBLIC_SUPABASE_URL as string; // e.g., 'https://your-project.supabase.co'
const SUPABASE_SERVICE_KEY = process.env.NEXT_PUBLIC_SUPABASE_PUBLISHABLE_KEY as string;
const CO_API_KEY = process.env.NEXT_PUBLIC_COHERE_API_KEY as string;

const supabase = createClient(SUPABASE_URL, SUPABASE_SERVICE_KEY);

const cohere = new CohereClientV2({
  token: CO_API_KEY,
});

async function analyzeAllUsers(): Promise<string> {
  console.log("🔍 Testing Supabase connection...");
  
  try {
    // Test 1: Check if we can connect to users table

    console.log("📋 Fetching users...");
    const { data: users, error: usersError } = await supabase
      .from('users')
      .select('*');
    
    if (usersError) {
      console.error('❌ Error fetching users:', usersError);
      return `Error fetching users: ${usersError.message}`;
    }
    
    console.log(`✅ Found ${users?.length || 0} users:`, users);
    
    // Test 2: Check activities for our test user
    const testUserId = '123e4567-e89b-12d3-a456-426614174000';
    console.log(`📋 Fetching activities for test user ${testUserId}...`);
    
    const { data: activities, error: activitiesError } = await supabase
      .from('activities')
      .select('*')
      .eq('user_id', testUserId)
      .order('timestamp', { ascending: false })
      .limit(10);
    
    if (activitiesError) {
      console.error('❌ Error fetching activities:', activitiesError);
      return `Error fetching activities: ${activitiesError.message}`;
    }
    
    console.log(`✅ Found ${activities?.length || 0} activities for test user`);
    console.log('Recent activities:', activities?.slice(0, 3));
    
    // Test 3: Check unprocessed activities count
    const { data: unprocessedActivities, error: unprocessedError } = await supabase
      .from('activities')
      .select('id, timestamp, domain, title')
      .eq('user_id', testUserId)
      .eq('processed', false);
    
    if (unprocessedError) {
      console.error('❌ Error fetching unprocessed activities:', unprocessedError);
      return `Error fetching unprocessed: ${unprocessedError.message}`;
    }
    
    console.log(`✅ Found ${unprocessedActivities?.length || 0} unprocessed activities`);
    

    // Prompt Cohere here
    if (unprocessedActivities && unprocessedActivities.length > 0) {
      const activityDescriptions = unprocessedActivities.map((a: any) => {
        return `At ${a.timestamp}, visited ${a.domain} - ${a.title}`;
      }).join('\n');

      const prompt = `summarize what the user has been doing, focus on what the user has potentially been interested in learning and what they have been learning\n\n${activityDescriptions}`;

      try {
        console.log("cohere time");
        const response = await cohere.chat({
          model: 'command-a-03-2025',
          messages: [
            {
              role: 'user',
              content: prompt,
            },
          ],
        });
        console.log('Cohere summary:', response);

        // Insert summary into summaries table
        // Extract only the text content from the Cohere response
        let summaryContent = null;
        if (response && response.message && Array.isArray(response.message.content)) {
          summaryContent = response.message.content; // Store the entire content array
        }
        const summaryPayload = {
          user_id: testUserId,
          summary: summaryContent, // Store the entire content array
          cohere_finish_reason: response.finishReason || null,
          cohere_usage: response.usage ? response.usage : null,
          cohere_prompt: prompt,
          source_activity_ids: unprocessedActivities.map((a: any) => a.id),
          prompt_generated_at: new Date().toISOString(),
        };
        const { error: summaryInsertError } = await supabase
          .from('summaries')
          .insert([summaryPayload]);
        if (summaryInsertError) {
          console.error('❌ Error inserting summary:', summaryInsertError);
        } else {
          console.log('✅ Summary inserted into summaries table');
        }
      } catch (cohereError) {
        console.error('❌ Error with Cohere:', cohereError);
      }
    }

    return `✅ Connection successful! Users: ${users?.length}, Activities: ${activities?.length}, Unprocessed: ${unprocessedActivities?.length}`;
  } catch (error) {
    console.error('💥 Fatal error:', error);
    return `Fatal error: ${error}`;
  }
}



// Test Cohere connection with a simple prompt
async function testCohereConnection(): Promise<string> {
  try {
    const response = await cohere.chat({
      model: 'command-a-03-2025',
      messages: [
        {
          role: 'user',
          content: 'hi',
        },
      ],
    });
    // Try to extract the text from the response
    if (response && response) {
      return `Cohere response: ${response}`;
    }
    // Fallback: print the whole response
    return `Cohere response: ${JSON.stringify(response)}`;
  } catch (error) {
    return `Cohere error: ${error}`;
  }
}

// Export for testing
export { analyzeAllUsers, testCohereConnection };
