"""Rule-based advice: profile x severity tier, English + Hindi.
General precautionary guidance, NOT medical advice. Have a clinician review
before any public launch.  Tier: 0 Good/Satisfactory, 1 Moderate, 2 Poor, 3 Very Poor/Severe.
"""
PROFILES = ["healthy", "asthma", "heart", "child", "elderly", "pregnant", "outdoor"]

ADVICE = {
    "en": {
        "healthy": ["Air is fine. Normal activity.",
                    "Fine for most; very sensitive people may notice irritation.",
                    "Cut back on long or intense outdoor exercise. Prefer a mask outdoors.",
                    "Avoid outdoor exercise. Wear an N95/FFP2 mask if you must go out."],
        "asthma": ["Normal activity. Keep your reliever inhaler with you as usual.",
                   "Limit long outdoor exertion. Keep your reliever inhaler handy.",
                   "Stay mostly indoors, avoid exercise outside, wear N95 outdoors. Follow your doctor's action plan.",
                   "Stay indoors with windows closed. Follow your doctor's action plan; seek care if symptoms worsen."],
        "heart": ["Normal activity.",
                  "Avoid heavy exertion outdoors.",
                  "Avoid outdoor exertion; wear N95 outdoors. Report chest discomfort or breathlessness.",
                  "Stay indoors. Seek medical help for chest pain, palpitations or severe breathlessness."],
        "child": ["Outdoor play is fine.",
                  "Shorten intense outdoor play.",
                  "Indoor activities for PE/play; N95-type mask (child fit) if travelling.",
                  "Keep children indoors. Skip outdoor assembly/PE."],
        "elderly": ["Normal activity.",
                    "Prefer shorter walks, avoid peak traffic hours.",
                    "Avoid outdoor walks; wear N95 if you must go out.",
                    "Stay indoors with windows closed. Check in on older family members."],
        "pregnant": ["Normal activity.",
                     "Limit long time near busy roads.",
                     "Avoid outdoor exertion; wear N95 outdoors.",
                     "Stay indoors; speak to your doctor if you feel unwell."],
        "outdoor": ["Normal work.",
                    "Take regular breaks away from traffic and dust.",
                    "Wear N95 on the job; rotate tasks and take indoor breaks.",
                    "Wear N95, minimise outdoor hours, and ask about shifting work times."],
    },
    "hi": {
        "healthy": ["हवा ठीक है। सामान्य गतिविधि करें।",
                    "ज़्यादातर लोगों के लिए ठीक है; बहुत संवेदनशील लोगों को हल्की जलन महसूस हो सकती है।",
                    "लंबी या तेज़ बाहरी कसरत कम करें। बाहर मास्क पहनना बेहतर है।",
                    "बाहर कसरत न करें। बाहर जाना ज़रूरी हो तो N95/FFP2 मास्क पहनें।"],
        "asthma": ["सामान्य गतिविधि करें। अपना रिलीवर इनहेलर हमेशा की तरह साथ रखें।",
                   "लंबे समय तक बाहर मेहनत न करें। रिलीवर इनहेलर पास रखें।",
                   "ज़्यादातर घर के अंदर रहें, बाहर कसरत न करें, बाहर N95 मास्क पहनें। अपने डॉक्टर की योजना का पालन करें।",
                   "खिड़कियाँ बंद करके घर के अंदर रहें। डॉक्टर की योजना का पालन करें; लक्षण बिगड़ें तो चिकित्सा सहायता लें।"],
        "heart": ["सामान्य गतिविधि करें।",
                  "बाहर भारी मेहनत से बचें।",
                  "बाहर मेहनत से बचें; बाहर N95 मास्क पहनें। सीने में बेचैनी या साँस फूलने पर डॉक्टर को बताएँ।",
                  "घर के अंदर रहें। सीने में दर्द, धड़कन तेज़ होने या बहुत साँस फूलने पर तुरंत चिकित्सा सहायता लें।"],
        "child": ["बाहर खेलना ठीक है।",
                  "तेज़ बाहरी खेल कम करें।",
                  "खेल और पीटी घर के अंदर कराएँ; बाहर जाना हो तो बच्चे के नाप का N95-प्रकार का मास्क लगाएँ।",
                  "बच्चों को घर के अंदर रखें। बाहर की असेंबली/पीटी न कराएँ।"],
        "elderly": ["सामान्य गतिविधि करें।",
                    "छोटी सैर करें और भारी ट्रैफ़िक के समय से बचें।",
                    "बाहर सैर न करें; जाना ज़रूरी हो तो N95 मास्क पहनें।",
                    "खिड़कियाँ बंद करके घर के अंदर रहें। घर के बुज़ुर्गों का हालचाल लेते रहें।"],
        "pregnant": ["सामान्य गतिविधि करें।",
                     "व्यस्त सड़कों के पास ज़्यादा देर न रहें।",
                     "बाहर मेहनत से बचें; बाहर N95 मास्क पहनें।",
                     "घर के अंदर रहें; तबीयत ठीक न लगे तो डॉक्टर से बात करें।"],
        "outdoor": ["सामान्य काम करें।",
                    "ट्रैफ़िक और धूल से दूर नियमित ब्रेक लें।",
                    "काम पर N95 मास्क पहनें; काम बदलते रहें और बीच-बीच में अंदर आराम करें।",
                    "N95 पहनें, बाहर के घंटे कम करें और काम का समय बदलने के बारे में पूछें।"],
    },
}

CATEGORY_HI = {"Good": "अच्छा", "Satisfactory": "संतोषजनक", "Moderate": "मध्यम",
               "Poor": "खराब", "Very Poor": "बहुत खराब", "Severe": "गंभीर"}

DISCLAIMER = {
    "en": "General precautionary guidance based on estimated air quality. Not medical advice. Follow your doctor's plan.",
    "hi": "अनुमानित वायु गुणवत्ता पर आधारित सामान्य सावधानी की सलाह। यह चिकित्सीय सलाह नहीं है। अपने डॉक्टर की योजना का पालन करें।",
}


def get_advice(profile, tier, lang="en"):
    return ADVICE.get(lang, ADVICE["en"])[profile][tier]
