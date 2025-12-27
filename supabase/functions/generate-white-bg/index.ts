import { serve } from "https://deno.land/std@0.168.0/http/server.ts";
import { createClient } from "https://esm.sh/@supabase/supabase-js@2.89.0";

const corsHeaders = {
  'Access-Control-Allow-Origin': '*',
  'Access-Control-Allow-Headers': 'authorization, x-client-info, apikey, content-type',
};

serve(async (req) => {
  if (req.method === 'OPTIONS') {
    return new Response(null, { headers: corsHeaders });
  }

  try {
    // Get the authorization header
    const authHeader = req.headers.get('Authorization');
    if (!authHeader) {
      return new Response(
        JSON.stringify({ error: "请先登录" }),
        { status: 401, headers: { ...corsHeaders, "Content-Type": "application/json" } }
      );
    }

    // Create Supabase client with user's auth token
    const supabaseUrl = Deno.env.get("SUPABASE_URL")!;
    const supabaseServiceKey = Deno.env.get("SUPABASE_SERVICE_ROLE_KEY")!;
    const supabase = createClient(supabaseUrl, supabaseServiceKey);

    // Verify the user's token
    const token = authHeader.replace('Bearer ', '');
    const { data: { user }, error: authError } = await supabase.auth.getUser(token);

    if (authError || !user) {
      console.error("Auth error:", authError);
      return new Response(
        JSON.stringify({ error: "认证失败，请重新登录" }),
        { status: 401, headers: { ...corsHeaders, "Content-Type": "application/json" } }
      );
    }

    console.log("User authenticated:", user.id);

    // Check and deduct credits
    const { data: deductResult, error: deductError } = await supabase.rpc('deduct_credit', {
      p_user_id: user.id
    });

    if (deductError) {
      console.error("Error deducting credits:", deductError);
      return new Response(
        JSON.stringify({ error: "积分扣除失败，请稍后重试" }),
        { status: 500, headers: { ...corsHeaders, "Content-Type": "application/json" } }
      );
    }

    if (!deductResult) {
      console.log("Insufficient credits for user:", user.id);
      return new Response(
        JSON.stringify({ error: "积分不足，请充值后继续使用" }),
        { status: 402, headers: { ...corsHeaders, "Content-Type": "application/json" } }
      );
    }

    console.log("Credit deducted successfully for user:", user.id);

    const { imageBase64 } = await req.json();
    
    if (!imageBase64) {
      throw new Error("No image provided");
    }

    const LOVABLE_API_KEY = Deno.env.get("LOVABLE_API_KEY");
    if (!LOVABLE_API_KEY) {
      throw new Error("LOVABLE_API_KEY is not configured");
    }

    console.log("Processing image with Gemini 3 Pro Image...");

    const response = await fetch("https://ai.gateway.lovable.dev/v1/chat/completions", {
      method: "POST",
      headers: {
        Authorization: `Bearer ${LOVABLE_API_KEY}`,
        "Content-Type": "application/json",
      },
      body: JSON.stringify({
        model: "google/gemini-3-pro-image-preview",
        messages: [
          {
            role: "user",
            content: [
              {
                type: "text",
                text: `Please professionally edit this image to create a high-quality e-commerce product photo with a pure white background (#FFFFFF).

BACKGROUND REMOVAL:
- Remove the existing background completely and replace with seamless pure white (#FFFFFF)
- Ensure clean, precise edges around the subject with no halos or artifacts
- Handle semi-transparent areas (like mesh fabric, lace, sheer materials) naturally

CLOTHING & APPAREL SPECIFIC ENHANCEMENTS:
- Preserve all fabric textures, patterns, prints, and material details (cotton weave, silk sheen, denim texture, knit patterns, etc.)
- Maintain accurate colors - do not oversaturate or wash out colors
- Keep all stitching, seams, buttons, zippers, labels, and embellishments clearly visible
- Preserve natural fabric folds and draping that show the garment's shape and fit
- Ensure logos, brand tags, and decorative elements remain sharp and readable
- Handle reflective materials (sequins, metallic fabrics, leather) with proper lighting

QUALITY REQUIREMENTS:
- Output should look like professional studio photography
- Maintain original image resolution and sharpness
- Natural, soft shadows are acceptable to add depth
- The product should appear centered and well-lit
- No color cast from the original background should remain on the product`
              },
              {
                type: "image_url",
                image_url: {
                  url: imageBase64
                }
              }
            ]
          }
        ],
        modalities: ["image", "text"]
      }),
    });

    if (!response.ok) {
      const errorText = await response.text();
      console.error("AI gateway error:", response.status, errorText);
      
      if (response.status === 429) {
        return new Response(
          JSON.stringify({ error: "请求过于频繁，请稍后重试" }),
          { status: 429, headers: { ...corsHeaders, "Content-Type": "application/json" } }
        );
      }
      if (response.status === 402) {
        return new Response(
          JSON.stringify({ error: "服务额度已用完，请联系管理员" }),
          { status: 402, headers: { ...corsHeaders, "Content-Type": "application/json" } }
        );
      }
      
      throw new Error(`AI gateway error: ${response.status}`);
    }

    const data = await response.json();
    console.log("Response received from AI gateway");

    const generatedImage = data.choices?.[0]?.message?.images?.[0]?.image_url?.url;
    
    if (!generatedImage) {
      console.error("No image in response:", JSON.stringify(data));
      throw new Error("No image generated in response");
    }

    console.log("Successfully generated white background image for user:", user.id);

    return new Response(
      JSON.stringify({ 
        success: true,
        image: generatedImage 
      }),
      { headers: { ...corsHeaders, "Content-Type": "application/json" } }
    );

  } catch (error) {
    console.error("Error in generate-white-bg function:", error);
    return new Response(
      JSON.stringify({ 
        error: error instanceof Error ? error.message : "处理失败，请稍后重试" 
      }),
      { 
        status: 500, 
        headers: { ...corsHeaders, "Content-Type": "application/json" } 
      }
    );
  }
});
