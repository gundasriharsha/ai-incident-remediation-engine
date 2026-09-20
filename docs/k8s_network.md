## Section 4: Kubernetes Ingress CoreDNS
- **Issue**: Pods failing to resolve internal cluster services or CoreDNS crashloopbackoff.
- **Root Cause**: CoreDNS configmap misconfigured or UDP 53 packets dropped by iptables/calico node policy.
- **Remediation**: Check CoreDNS logs via `kubectl -n kube-system logs -l k8s-app=kube-dns`. Restart CoreDNS pods: `kubectl -n kube-system rollout restart deployment coredns`.