import sys

def modify(filepath):
    with open(filepath, 'r') as f:
        content = f.read()

    if 'export default function PatientPayPage' in content:
        content = content.replace("export default function PatientPayPage() {", "function PatientPayPageContent() {")
        content = content.replace("'use client';", "'use client';\nimport { Suspense } from 'react';")
        content += "\nexport default function PatientPayPage() { return <Suspense fallback={<div>Loading...</div>}><PatientPayPageContent /></Suspense>; }\n"
    elif 'export default function PatientReceiptPage' in content:
        content = content.replace("export default function PatientReceiptPage() {", "function PatientReceiptPageContent() {")
        content = content.replace("'use client';", "'use client';\nimport { Suspense } from 'react';")
        content += "\nexport default function PatientReceiptPage() { return <Suspense fallback={<div>Loading...</div>}><PatientReceiptPageContent /></Suspense>; }\n"

    with open(filepath, 'w') as f:
        f.write(content)

modify('app/portal/patient/pay/page.tsx')
modify('app/portal/patient/receipt/page.tsx')
