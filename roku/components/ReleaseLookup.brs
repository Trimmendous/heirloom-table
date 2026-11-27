sub init()
    m.top.functionName = "fetchRelease"
end sub

sub fetchRelease()
    port = CreateObject("roMessagePort")
    transfer = CreateObject("roUrlTransfer")
    transfer.SetMessagePort(port)
    transfer.SetCertificatesFile("common:/certs/ca-bundle.crt")
    transfer.AddHeader("User-Agent", "Culinote")
    transfer.AddHeader("Accept", "application/vnd.github+json")
    transfer.SetUrl(m.top.endpoint)
    result = { status: 0 }
    if transfer.AsyncGetToString()
        event = Wait(12000, port)
        if event <> invalid
            result.status = event.GetResponseCode()
            if result.status = 200 then result.release = ParseJson(event.GetString())
        else
            transfer.AsyncCancel()
        end if
    end if
    m.top.result = result
end sub
