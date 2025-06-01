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
    "Output ONLY valid JSON in the following structure, with no extra text or explanation.\n"
    "The `full_brief` field should be a detailed outline of the blog, using bullet points or numbered sections, not a narrative paragraph.\n"
    "Example:\n"
    "{{\n"
    "  \"title\": \"NFC Tag Management: A Complete Guide for Businesses\",\n"
    "  \"introduction\": \"Learn how to manage NFC tags effectively for your business.\",\n"
    "  \"audience\": \"Business owners, IT managers, marketers interested in NFC technology.\",\n"
    "  \"search_intent\": \"Find out how to set up and optimize NFC tag management.\",\n"
    "  \"talking_points\": [\"Introduction to NFC tag management\", \"Step-by-step guide to setup\", \"Review of top NFC tag management software (Seritag, tag.link)\", \"Case study: Successful business implementation\", \"Tips for selecting NFC tags and software (security, scalability, cost-effectiveness)\", \"Resources and further reading\"],\n"
    "  \"word_count\": 1500,\n"
    "  \"full_brief\": \"1. Introduction to NFC tag management\\n2. Step-by-step guide to setting up NFC tag management\\n3. Review of top NFC tag management software (Seritag, tag.link)\\n4. Case study: Successful business implementation\\n5. Tips for selecting NFC tags and software (security, scalability, cost-effectiveness)\\n6. Resources and further reading\"\n"
    "}}\n"
    "\nResearch data:\n{data}"
)

REDDIT_SUMMARY_PROMPT = (
    "Summarize the main themes and top discussions from Reddit for the keyword: '{keyword}'. "
    "Focus on what people are asking, problems, and popular opinions."
) 