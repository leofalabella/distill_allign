import os
import logging
from seed_generator import MathProbGenerator, TeacherSynthesizer
from response_parser import ResponseParser  
from dotenv import load_dotenv
load_dotenv()

logging.basicConfig(level=logging.INFO)

def main():
    key = os.getenv("OPEN_ROUTER_API_KEY")
    print("OPEN_ROUTER_API_KEY loaded:", bool(key), "len:", 0 if not key else len(key))

    gen = MathProbGenerator()
    synth = TeacherSynthesizer(api_key=os.getenv(key))
    parser = ResponseParser()

    for i in range(3):
        skeleton = gen.generate_skeleton()
        logging.info(f"\n--- SAMPLE {i} ---")
        logging.info(f"SKELETON: {skeleton}")

        raw = synth.call_teacher(skeleton)
        logging.info("RAW OUTPUT:\n" + raw)

        parsed = parser.parse(raw, strict=True)
        if not parsed:
            logging.warning("Parse failed (strict).")
            continue

        logging.info(f"PARSED FINAL ANSWER: {parsed['final_answer']}")
        logging.info(f"EXPECTED ANSWER: {skeleton['answer']}")

        if parsed['final_answer'] == skeleton['answer']:
            logging.info("Pass: aswer matches ground truth")
        else:
            logging.warning("Fail: asnwer mismatch")
        

        # quick format sanity
        logging.info(f"PROBLEM (first 120 chars): {parsed['problem'][:120]!r}")
        logging.info(f"REASONING (first 120 chars): {parsed['reasoning'][:120]!r}")


if __name__ == "__main__":
    main()
        

