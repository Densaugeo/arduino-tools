/test\/[A-Za-z_]+.py::/ {
  # Remove 'test' since it's in every test name
  gsub(/test\//, "", $1);
  gsub(/test_/, "", $1);
  
  # Add spacing and yellow color to [foo]
  non_printing = 5*gsub(/\[/, " [\x1B[93m", $1);
  non_printing += 4*gsub(/\]/, "\x1B[0m]", $1);
  
  # Add spacing and cyan color to <foo>(
  non_printing += 5*gsub(/</, " <\x1B[96m", $1);
  non_printing += 4*gsub(/>\(/, "\x1B[0m>(", $1);
  
  # Add spacing and yellow color to (foo)
  non_printing += 5*gsub(/\(/, " (\x1B[93m", $1);
  non_printing += 4*gsub(/\)/, "\x1B[0m)", $1);
  
  # Add spacing and yellow color to =foo
  #non_printing += 5*gsub(/=/, " = \x1B[93m", $1);
  
  # Add spacing and violet color to ->foo
  non_printing += 5*gsub(/->/, " -> \x1B[95m", $1);
  
  # Add spacing and orange color to ! at end of line
  non_printing += 5*gsub(/!$/, " \x1B[33m!", $1);
  
  gsub(",", ", ", $1);
  
  printf("%-*s\x1B[0m", 65 + non_printing, $1);
  $1="";
  print $0;
  next;
}

1 {
  print $0;
}
