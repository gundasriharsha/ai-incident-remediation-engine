# Enterprise Infrastructure Troubleshooting Runbook

## Section 1: Compute & BMC Management
- **Issue**: Redfish API returns HTTP 401 Unauthorized or authentication handshake failure.
- **Root Cause**: The BMC credentials for iLO (HPE) or iDRAC (Dell) have expired or desynchronized with the secrets manager.
- **Remediation**: Retrieve current service account token from HashiCorp Vault. Run password rotation playbook `rotate_bmc_creds.yml` and verify Redfish `/redfish/v1/Systems` endpoint connectivity.

## Section 2: Container Orchestration & Docker
- **Issue**: HTTP 503 Service Unavailable on microservice ingress or sudden container crash.
- **Root Cause**: Backend pods or Docker containers hitting Linux cgroup OOM (Out Of Memory) limits due to memory leak.
- **Remediation**: Check `dmesg -T | grep -i oom` on the host. Scale replica count via Docker Compose or update `mem_limit` in the deployment YAML from 2GB to 4GB. Restart the container service.

## Section 3: Storage & SAN Fabric
- **Issue**: Multipath I/O latency alert or SCSI sense key status 0x82.
- **Root Cause**: SAN fibre-channel switch zoning mismatch or target LUN dropped connection during firmware patch.
- **Remediation**: Run `rescan-scsi-bus.sh` on the host. Verify HBA status via `cat /sys/class/fc_host/host*/port_state`. Re-bind multipath daemon using `multipath -r`.s