local injected_url_found = false

wpull_hook.callbacks.resolve_dns = function(host)
  --  print('resolve_dns', host)
  assert(host == 'localhost')
  return '127.0.0.1'
end

wpull_hook.callbacks.accept_url = function(url_info, record_info, verdict, reasons)
  --  print('accept_url', url_info)
  assert(url_info['url'])
  local accepted_paths = {
    ['/robots.txt'] = true,
    ['/'] = true,
    ['/test_script'] = true
  }
  assert(accepted_paths[url_info['path']])
  assert(record_info['url'])
  assert(reasons['filters']['HTTPFilter'])

  if url_info['path'] == '/' then
    assert(verdict)
  elseif url_info['path'] == '/test_script' then
    assert(not verdict)
    verdict = true
  end
  
  return verdict
end

wpull_hook.callbacks.handle_response = function(url_info, http_info)
  --  print('handle_response', url_info)

  if url_info['path'] == '/' then
    assert(http_info['status_code'] == 200)
  elseif url_info['path'] == '/test_script' then
    injected_url_found = true
  end

  return wpull_hook.actions.NORMAL
end

wpull_hook.callbacks.handle_error = function(url_info, error)
  --  print('handle_response', url_info, error)
  assert(error['error'])
  return wpull_hook.actions.NORMAL
end

wpull_hook.callbacks.get_urls = function(filename, url_info, document_info)
  --  print('get_urls', filename)
  assert(filename)
  local file = io.open(filename, 'r')
  assert(file)
  assert(url_info['url'])

  if url_info['path'] == '/' then
    local url_table = {}
    table.insert(url_table, {['url'] = 'http://localhost:'..url_info['port']..'/test_script'})
    return url_table
  end

  return nil
end

wpull_hook.callbacks.finish_statistics = function(start_time, end_time, num_urls, bytes_downloaded)
  --  print('finish_statistics', start_time)
  assert(start_time)
  assert(end_time)
end

wpull_hook.callbacks.exit_status = function(exit_code)
  --  print('exit_status', exit_code)
  assert(exit_code == 0)
  assert(injected_url_found)
  return 42
end
