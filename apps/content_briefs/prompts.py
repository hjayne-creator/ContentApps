# prompts.py

OPENAI_KEYWORD_PROMPT = (
    "As an SEO expert, generate 3 related SEO-friendly search queries based on the keyword: '{keyword}'. "
    "Return the queries as a plain list, with no numbering, no bullet points, and no extra text or formatting. "
    "Output the queries as a JSON array like: [\"query1\", \"query2\", \"query3\"]"
)

WEBSITE_SUMMARY_PROMPT = (
    "Summarize what this website does:\n\n{text}"
)

BRIEF_BUILDER_PROMPT = (
    "You are an expert content analyst who excels at writing SEO-optimized blog briefs. Using the following research data, generate a comprehensive blog brief for a writer.\n"
    "Output ONLY valid JSON in the following structure, with no extra text or explanation:\n"
    "{\n"
    "  \"title\": {\n"
    "    \"main_title\": \"Main title of the article\",\n"
    "    \"meta_title\": \"SEO-optimized meta title (50-60 chars)\",\n"
    "    \"meta_description\": \"SEO-optimized meta description (150-160 chars)\"\n"
    "  },\n"
    "  \"audience\": {\n"
    "    \"primary_audience\": \"Detailed description of primary audience\",\n"
    "    \"secondary_audience\": \"Detailed description of secondary audience\",\n"
    "    \"pain_points\": [\"Pain point 1\", \"Pain point 2\", \"Pain point 3\"],\n"
    "    \"goals\": [\"Goal 1\", \"Goal 2\", \"Goal 3\"]\n"
    "  },\n"
    "  \"content_structure\": {\n"
    "    \"introduction\": \"Engaging introduction paragraph\",\n"
    "    \"main_sections\": [\n"
    "      {\n"
    "        \"heading\": \"Section 1 Title\",\n"
    "        \"key_points\": [\"Point 1\", \"Point 2\", \"Point 3\"],\n"
    "        \"subsections\": [\n"
    "          {\n"
    "            \"heading\": \"Subsection 1\",\n"
    "            \"content\": \"Subsection content\"\n"
    "          }\n"
    "        ]\n"
    "      }\n"
    "    ],\n"
    "    \"conclusion\": \"Strong conclusion paragraph\"\n"
    "  },\n"
    "  \"seo_elements\": {\n"
    "    \"search_intent\": \"Detailed description of search intent\",\n"
    "    \"word_count\": 1500,\n"
    "  },\n"
    "  \"content_guidelines\": {\n"
    "    \"tone\": \"Description of content tone\",\n"
    "    \"style\": \"Description of writing style\",\n"
    "  }\n"
    "}\n"
    "\nResearch data:\n{data}"
)

REDDIT_SUMMARY_PROMPT = (
    "Summarize the main themes and top discussions from Reddit for the keyword: '{keyword}'. "
    "Focus on what people are asking, problems, and popular opinions."
) 