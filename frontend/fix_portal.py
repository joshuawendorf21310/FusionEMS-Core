path = '/workspaces/FusionEMS-Core/frontend/app/portal/page.tsx'
with open(path, 'r') as f:
    c = f.read()
c = c.replace('actionLabel="Refresh Data"\n            onAction={() => window.location.reload()}', 'action={<button onClick={() => window.location.reload()} className="quantum-btn mt-4">Refresh Data</button>}')
c = c.replace('actionLabel="Refresh Data"\n          onAction={() => window.location.reload()}', 'action={<button onClick={() => window.location.reload()} className="quantum-btn mt-4">Refresh Data</button>}')
c = c.replace('          actionLabel="Refresh Data"\n          onAction={() => window.location.reload()}', '          action={<button onClick={() => window.location.reload()} className="quantum-btn mt-4">Refresh Data</button>}')
with open(path, 'w') as f:
    f.write(c)
