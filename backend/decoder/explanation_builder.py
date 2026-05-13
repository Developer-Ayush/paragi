class ExplanationBuilder:
    def build(self, ir):
        return ""

    def build_narrative(self, meaning):
        facts = meaning.get("facts", [])
        if not facts:
            return ""
        return ". ".join(facts) + "."
